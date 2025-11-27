"""
AI Voice Bot - Responds to questions using voice input/output and LLM API

Note: Audio libraries are imported lazily inside the VoiceBot class so that
server deployments (e.g., Render) don't need pyaudio/pyttsx3 installed.
"""
import sys
from config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    VOICE_SPEED,
    VOICE_VOLUME,
    SYSTEM_PROMPT
)


class VoiceBot:
    def __init__(self):
        """Initialize the voice bot with speech recognition and text-to-speech"""
        try:
            import speech_recognition as sr  # type: ignore
            import pyttsx3  # type: ignore
            self._sr = sr
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            self.tts_engine = pyttsx3.init()
        except Exception as e:
            raise RuntimeError(
                "Voice mode requires local audio dependencies. "
                "Please install: speechrecognition, pyttsx3, pyaudio"
            ) from e
        
        # Configure TTS
        self.tts_engine.setProperty('rate', VOICE_SPEED)
        self.tts_engine.setProperty('volume', VOICE_VOLUME)
        
        # Try to set a more natural voice (if available)
        voices = self.tts_engine.getProperty('voices')
        if voices:
            # Prefer a female voice if available, otherwise use first available
            for voice in voices:
                if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                    self.tts_engine.setProperty('voice', voice.id)
                    break
            else:
                self.tts_engine.setProperty('voice', voices[0].id)
        
        # Initialize LLM client
        self.llm_client = self._initialize_llm()
        
        print("Voice Bot initialized successfully!")
        print("Listening for your questions...")
    
    def _generate_greeting(self):
        """Generate a short first-person greeting via the LLM using the persona"""
        try:
            prompt = (
                "Give a warm, natural 1–2 sentence greeting in first person as me. "
                "Do not mention being an AI or assistant. Keep it friendly and real."
            )
            greeting = self.llm_client.get_response(prompt)
            if greeting and isinstance(greeting, str):
                return greeting.strip()
        except Exception:
            pass
        # Safe fallback if LLM unavailable
        return "Hey! Good to connect — happy to share about me. What would you like to know?"

    def _initialize_llm(self):
        """Initialize the LLM client based on configuration"""
        if GROQ_API_KEY:
            return GroqClient(GROQ_API_KEY, GROQ_MODEL)
        elif OPENAI_API_KEY:
            return OpenAIClient(OPENAI_API_KEY, OPENAI_MODEL)
        else:
            print("Warning: No API key found. Using fallback responses.")
            return FallbackClient()
    
    def listen(self):
        """Listen for voice input and convert to text"""
        with self.microphone as source:
            # Adjust for ambient noise
            print("Adjusting for ambient noise... Please wait.")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("Listening...")
            
            try:
                # Listen for audio
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                print("Processing speech...")
                
                # Recognize speech using Google's speech recognition
                text = self.recognizer.recognize_google(audio)
                print(f"You said: {text}")
                return text
            except self._sr.WaitTimeoutError:
                print("No speech detected. Please try again.")
                return None
            except self._sr.UnknownValueError:
                print("Could not understand audio. Please try again.")
                return None
            except self._sr.RequestError as e:
                print(f"Error with speech recognition service: {e}")
                return None
    
    def speak(self, text):
        """Convert text to speech and speak it"""
        print(f"Bot: {text}")
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()
    
    def get_response(self, question):
        """Get response from LLM"""
        return self.llm_client.get_response(question)
    
    def run(self):
        """Main conversation loop"""
        # Greeting via LLM (first-person, authentic)
        greeting = self._generate_greeting()
        self.speak(greeting)
        
        while True:
            try:
                # Listen for question
                question = self.listen()
                
                if question is None:
                    continue
                
                # Check for exit commands
                if any(word in question.lower() for word in ['exit', 'quit', 'goodbye', 'bye']):
                    self.speak("Goodbye! It was nice talking with you.")
                    break
                
                # Get response from LLM
                response = self.get_response(question)
                
                # Speak the response
                if response:
                    self.speak(response)
                else:
                    self.speak("I'm sorry, I couldn't generate a response. Please try again.")
                    
            except KeyboardInterrupt:
                print("\nExiting...")
                self.speak("Goodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
                self.speak("I encountered an error. Let's try again.")


class GroqClient:
    """Groq API client - Fast inference with open-source models"""
    def __init__(self, api_key, model):
        try:
            from groq import Groq
            self.client = Groq(api_key=api_key)
            self.model = model
            self.conversation_history = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ]
        except ImportError:
            print("Groq library not installed. Install with: pip install groq")
            raise
    
    def get_response(self, question):
        """Get response from Groq API"""
        try:
            # Add user question to history
            self.conversation_history.append({"role": "user", "content": question})
            
            # Get response from API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                # Allow longer answers so responses are not cut off mid-sentence
                max_tokens=800,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content
            
            # Add assistant response to history
            self.conversation_history.append({"role": "assistant", "content": answer})
            
            # Keep conversation history manageable (last 10 messages)
            if len(self.conversation_history) > 20:
                self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-19:]
            
            return answer
        except Exception as e:
            print(f"Groq API Error: {e}")
            return None


class OpenAIClient:
    """OpenAI API client"""
    def __init__(self, api_key, model):
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
            self.model = model
            self.conversation_history = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ]
        except ImportError:
            print("OpenAI library not installed. Install with: pip install openai")
            raise
    
    def get_response(self, question):
        """Get response from OpenAI API"""
        try:
            # Add user question to history
            self.conversation_history.append({"role": "user", "content": question})
            
            # Get response from API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                # Allow longer answers so responses are not cut off mid-sentence
                max_tokens=800,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content
            
            # Add assistant response to history
            self.conversation_history.append({"role": "assistant", "content": answer})
            
            # Keep conversation history manageable (last 10 messages)
            if len(self.conversation_history) > 20:
                self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-19:]
            
            return answer
        except Exception as e:
            print(f"OpenAI API Error: {e}")
            return None


class HuggingFaceClient:
    """Hugging Face API client (free alternative)"""
    def __init__(self):
        # Use a text generation model that works better for Q&A
        self.api_url = f"https://api-inference.huggingface.co/models/{HUGGINGFACE_MODEL}"
        self.headers = {}
        self.conversation_context = SYSTEM_PROMPT
        # Note: Some models don't require API key, but you can add one if needed
        # self.headers = {"Authorization": f"Bearer {YOUR_HF_TOKEN}"}
    
    def get_response(self, question):
        """Get response from Hugging Face API"""
        try:
            import requests
            
            # Format prompt for text generation
            prompt = f"{self.conversation_context}\n\nUser: {question}\nAssistant:"
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    # Allow longer generations for detailed answers
                    "max_new_tokens": 512,
                    "return_full_text": False
                }
            }
            
            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    generated_text = result[0].get('generated_text', '')
                    # Clean up the response
                    generated_text = generated_text.strip()
                    # Remove any repeated prompts
                    if "Assistant:" in generated_text:
                        generated_text = generated_text.split("Assistant:")[-1].strip()
                    return generated_text if generated_text else None
                elif isinstance(result, dict) and 'generated_text' in result:
                    return result['generated_text'].strip()
            elif response.status_code == 503:
                # Model is loading, wait and retry
                print("Model is loading, please wait...")
                import time
                time.sleep(5)
                return self.get_response(question)
            else:
                print(f"Hugging Face API Error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Hugging Face API Error: {e}")
            return None


class FallbackClient:
    """Basic offline fallback"""
    def get_response(self, question):
        q = question.lower()
        if "life" in q:
            return "I was born and brought up in Indore, and my journey so far has been about curiosity and growth."
        if "superpower" in q:
            return "I’d say my biggest superpower is adaptability. I learn fast and adjust to challenges quickly."
        if "grow" in q:
            return "I’m focusing on growing in AI, software, finance, and real estate — all areas that excite me."
        if "boundaries" in q:
            return "Whenever I fear being mediocre, I push harder — I believe real growth begins there."
        return "That’s a great question — I’d like to reflect on that a bit more."


if __name__ == "__main__":
    try:
        bot = VoiceBot()
        bot.run()
    except Exception as e:
        print(f"Failed to initialize voice bot: {e}")
        sys.exit(1)

