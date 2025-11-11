"""
Flask web application for AI Voice Bot
"""
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import sys
from config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    SYSTEM_PROMPT
)

# Import LLM clients from voice_bot
from voice_bot import GroqClient, OpenAIClient, FallbackClient

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

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
        
        # Get response from LLM
        response = llm_client.get_response(question)
        
        if response:
            return jsonify({
                'success': True,
                'response': response
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to generate response'
            }), 500
            
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

