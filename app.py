"""
Flask web application for AI Voice Bot
"""
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
import sys
import json
import requests
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    SYSTEM_PROMPT,
    N8N_WEBHOOK_URL,
    GOOGLE_CLIENT_ID,
    SECRET_KEY,
)

# Import LLM clients from voice_bot
from voice_bot import GroqClient, OpenAIClient, FallbackClient

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = SECRET_KEY
CORS(app, supports_credentials=True)

# Initialize LLM client
def get_llm_client():
    """Initialize the LLM client based on configuration"""
    try:
        if GROQ_API_KEY:
            print(f"Initializing Groq client with model: {GROQ_MODEL}")
            return GroqClient(GROQ_API_KEY, GROQ_MODEL)
        elif OPENAI_API_KEY:
            print(f"Initializing OpenAI client with model: {OPENAI_MODEL}")
            return OpenAIClient(OPENAI_API_KEY, OPENAI_MODEL)
        else:
            print("No API keys found. Using fallback client.")
            return FallbackClient()
    except Exception as e:
        print(f"Error initializing LLM client: {e}")
        print("Falling back to FallbackClient")
        return FallbackClient()

try:
    llm_client = get_llm_client()
    print(f"LLM client initialized: {type(llm_client).__name__}")
except Exception as e:
    print(f"Critical error initializing LLM client: {e}")
    llm_client = FallbackClient()

@app.route('/')
def index():
    """Main page"""
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"Error rendering template: {e}")
        return f"Error loading page: {str(e)}", 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat requests"""
    try:
        data = request.json
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'error': 'No question provided'}), 400
        
        # Check if user is authenticated and if question is about booking
        user_email = session.get('user_email')
        user_name = session.get('user_name')
        is_authenticated = session.get('authenticated', False)
        
        # Detect booking intent (keywords that suggest user wants to book)
        booking_keywords = ['book', 'schedule', 'appointment', 'interview', 'meeting', 'slot', 'call', 'connect', 'talk']
        question_lower = question.lower()
        is_booking_intent = any(keyword in question_lower for keyword in booking_keywords)
        
        # If user is authenticated and wants to book, add their info to context
        if is_authenticated and is_booking_intent and user_name and user_email:
            # Add user context before the question so LLM knows their info
            context_message = f"[User Info: Name: {user_name}, Email: {user_email}]"
            enhanced_question = f"{context_message}\n\nUser: {question}"
            print(f"[AUTH] Using authenticated user info for booking: {user_name} ({user_email})")
        else:
            enhanced_question = question
        
        # Get response from LLM
        raw_response = llm_client.get_response(enhanced_question)

        if not raw_response:
            return jsonify({
                'success': False,
                'error': 'Failed to generate response'
            }), 500

        response_text = raw_response
        booking_payload = None
        booking_result = None

        # Detect special meeting booking marker from the LLM response
        marker = "[[BOOK_INTERVIEW]]"  # Keep marker name for backward compatibility
        if marker in raw_response:
            try:
                # Split conversational text and machine-readable JSON marker
                conversational_part, marker_part = raw_response.rsplit(marker, 1)
                response_text = conversational_part.strip()

                marker_json_str = marker_part.strip()
                if marker_json_str:
                    # Be defensive: extract substring between first '{' and last '}' to avoid trailing text
                    start_idx = marker_json_str.find('{')
                    end_idx = marker_json_str.rfind('}')
                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        json_str = marker_json_str[start_idx:end_idx + 1]
                    else:
                        json_str = marker_json_str

                    booking_payload = json.loads(json_str)
                    
                    # Normalize date format for Google Calendar (ensure ISO format with seconds)
                    # Check if time part has format HH:MM (needs :00 seconds) vs HH:MM:SS (already has seconds)
                    def normalize_datetime(dt_str):
                        if not dt_str or "T" not in dt_str:
                            return dt_str
                        # Split date and time parts
                        if "T" in dt_str:
                            date_part, time_part = dt_str.split("T", 1)
                            # Check if time part has seconds (2 colons) or just minutes (1 colon)
                            if time_part.count(":") == 1:
                                # Format is HH:MM, add :00 for seconds
                                return f"{date_part}T{time_part}:00"
                            # Already has seconds or timezone, return as is
                            return dt_str
                        return dt_str
                    
                    if "start" in booking_payload:
                        booking_payload["start"] = normalize_datetime(booking_payload["start"])
                    
                    if "end" in booking_payload:
                        booking_payload["end"] = normalize_datetime(booking_payload["end"])
                    
                    # Normalize timezone: convert common abbreviations to IANA timezone
                    if "timezone" in booking_payload:
                        tz = booking_payload["timezone"].upper()
                        tz_map = {
                            "IST": "Asia/Kolkata",
                            "PST": "America/Los_Angeles",
                            "EST": "America/New_York",
                            "GMT": "UTC",
                            "UTC": "UTC"
                        }
                        if tz in tz_map:
                            booking_payload["timezone"] = tz_map[tz]
                    
                    # ALWAYS use authenticated user info if available (override any LLM-provided values)
                    if session.get('authenticated'):
                        authenticated_name = session.get('user_name', '')
                        authenticated_email = session.get('user_email', '')
                        if authenticated_name:
                            booking_payload['name'] = authenticated_name
                            print(f"[BOOKING] Using authenticated name: {authenticated_name}")
                        if authenticated_email:
                            booking_payload['email'] = authenticated_email
                            print(f"[BOOKING] Using authenticated email: {authenticated_email}")
                    
                    print(f"[BOOKING] Detected booking payload: {booking_payload}")
            except Exception as e:
                print(f"[BOOKING] Error parsing booking marker: {e} | raw marker: {marker_part!r}")
                # Fallback: keep full text, no booking payload
                response_text = raw_response
                booking_payload = None

        # If we have booking data and an n8n webhook URL configured, trigger the workflow
        if booking_payload:
            if not N8N_WEBHOOK_URL:
                print("[BOOKING] Booking payload present but N8N_WEBHOOK_URL is not set. Skipping webhook call.")
            else:
                try:
                    print(f"[BOOKING] Sending booking payload to n8n: {N8N_WEBHOOK_URL}")
                    n8n_response = requests.post(
                        N8N_WEBHOOK_URL,
                        json=booking_payload,
                        timeout=10
                    )
                    print(f"[BOOKING] n8n response status: {n8n_response.status_code}")
                    n8n_response.raise_for_status()
                    # Try to parse JSON response from n8n (if any)
                    try:
                        booking_result = n8n_response.json()
                    except Exception:
                        booking_result = {"status": "success", "raw": n8n_response.text}
                except Exception as e:
                    print(f"[BOOKING] Error calling n8n webhook: {e}")
                    booking_result = {"status": "error", "error": str(e)}

        # Always return a successful chat response here; booking_result may be None
        return jsonify({
            'success': True,
            'response': response_text,
            'booking': booking_result
        })
            
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'llm_type': type(llm_client).__name__
    })

@app.route('/api/reset', methods=['POST'])
def reset():
    """Reset conversation context (start a new conversation)"""
    try:
        global llm_client
        llm_client = get_llm_client()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error resetting conversation: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auth/google', methods=['POST'])
def google_auth():
    """Verify Google ID token and create session"""
    try:
        data = request.json
        token = data.get('token', '').strip()
        
        if not token:
            return jsonify({'error': 'No token provided'}), 400
        
        if not GOOGLE_CLIENT_ID:
            return jsonify({'error': 'Google OAuth not configured'}), 500
        
        # Verify the token
        try:
            idinfo = id_token.verify_oauth2_token(
                token, 
                google_requests.Request(), 
                GOOGLE_CLIENT_ID
            )
            
            # Get user info
            user_email = idinfo.get('email')
            user_name = idinfo.get('name', user_email.split('@')[0])
            user_picture = idinfo.get('picture', '')
            
            # Store in session
            session['user_email'] = user_email
            session['user_name'] = user_name
            session['user_picture'] = user_picture
            session['authenticated'] = True
            
            print(f"[AUTH] User authenticated: {user_name} ({user_email})")
            
            return jsonify({
                'success': True,
                'user': {
                    'name': user_name,
                    'email': user_email,
                    'picture': user_picture
                }
            })
        except ValueError as e:
            print(f"[AUTH] Token verification failed: {e}")
            return jsonify({'error': 'Invalid token'}), 401
            
    except Exception as e:
        print(f"Error in Google auth: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/user', methods=['GET'])
def get_user():
    """Get current user info from session"""
    if session.get('authenticated'):
        return jsonify({
            'success': True,
            'user': {
                'name': session.get('user_name'),
                'email': session.get('user_email'),
                'picture': session.get('user_picture')
            }
        })
    else:
        return jsonify({
            'success': False,
            'user': None
        })

@app.route('/api/auth/config', methods=['GET'])
def auth_config():
    """Get Google OAuth2 client ID for frontend"""
    return jsonify({
        'googleClientId': GOOGLE_CLIENT_ID
    })

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout user"""
    session.clear()
    return jsonify({'success': True})

@app.route('/test')
def test():
    """Test route to verify Flask is working"""
    return jsonify({
        'message': 'Flask is working!',
        'routes': ['/', '/api/chat', '/api/health', '/test']
    })

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Not Found',
        'message': 'The requested URL was not found on the server.',
        'available_routes': ['/', '/api/chat', '/api/health', '/test']
    }), 404

if __name__ == '__main__':
    print("Starting Flask server...")
    print("Open http://localhost:5000 in your browser")
    app.run(debug=True, host='0.0.0.0', port=5000)

