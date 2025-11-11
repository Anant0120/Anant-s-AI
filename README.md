# AI Voice Bot

A beautiful web-based voice-enabled chatbot that responds to questions about **you** (the user) using speech recognition, LLM APIs, and text-to-speech. The bot answers personal questions as if it's speaking from your perspective.

## Features

- 🎨 **Beautiful Web Interface**: Modern dark-themed UI with Flask
- 🎤 **Voice Input**: Speak your questions naturally using Web Speech API
- 🤖 **AI Responses**: Uses Groq, OpenAI, or Hugging Face APIs
- 🔊 **Voice Output**: Speaks responses back to you
- 🎭 **Siri-like Animations**: Lottie animations for listening/speaking states
- 💬 **Conversational**: Maintains context during the conversation
- 📱 **Responsive**: Works on desktop and mobile devices

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note for Windows users**: If you encounter issues installing `pyaudio`, you may need to:
- Install it from a pre-built wheel: `pip install pipwin && pipwin install pyaudio`
- Or download a wheel from [here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio)

### 2. Configure API Keys (Optional)

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Then edit `.env` and add your API key:

**Recommended - Groq (Fast & Free tier available):**
```
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
```

**Or use OpenAI:**
```
OPENAI_API_KEY=your_openai_api_key_here
```

**Or use Hugging Face (free, no API key needed):**
```
USE_HUGGINGFACE=true
```

### 3. Run the Bot

**Web Interface (Recommended):**
```bash
python app.py
```
Then open http://localhost:5000 in your browser.

**Command Line Interface:**
```bash
python voice_bot.py
```

## Usage (Web Interface)

1. Run `python app.py` to start the Flask server
2. Open http://localhost:5000 in your browser
3. Click the microphone button or type your question
4. The bot will show animations while listening/speaking
5. Responses appear in the chat and are spoken aloud
6. You can type questions or use voice input

**Voice Commands:**
- Click the microphone button to start voice input
- Speak your question clearly
- The bot will automatically process and respond

## Example Questions

The bot will answer these questions **as you** (first person):

- "What should we know about your life story in a few sentences?"
- "What's your #1 superpower?"
- "What are the top 3 areas you'd like to grow in?"
- "What misconception do your coworkers have about you?"
- "How do you push your boundaries and limits?"

**Note**: The bot uses Groq/OpenAI to generate personalized responses based on your questions. It responds in first person (I, me, my) as if you're speaking about yourself.

## Configuration

Edit `config.py` or `.env` to customize:
- API provider (OpenAI or Hugging Face)
- Voice speed and volume
- System prompt for AI personality

### API Options

1. **Groq (Recommended)**: Fast inference with free tier available
   - Get API key from: https://console.groq.com/keys
   - Set `GROQ_API_KEY` in `.env`
   - Fast models: `llama-3.1-8b-instant`, `mixtral-8x7b-32768`, `gemma-7b-it`
   - Free tier includes generous rate limits

2. **OpenAI (ChatGPT)**: Requires API key, best quality responses
   - Get API key from: https://platform.openai.com/api-keys
   - Set `OPENAI_API_KEY` in `.env`

3. **Hugging Face (Free)**: No API key needed for basic models
   - Set `USE_HUGGINGFACE=true` in `.env`
   - May have slower response times or model loading delays

4. **Fallback Mode**: Works without any API key
   - Uses predefined responses for common questions
   - Good for testing or offline use

## Troubleshooting

- **Microphone not working**: 
  - Check your system's microphone permissions
  - Ensure microphone is not muted or disabled
  - Try speaking louder or closer to the microphone

- **Speech recognition errors**: 
  - Ensure you have an internet connection (uses Google's speech recognition)
  - Speak clearly and wait for the "Listening..." prompt
  - Reduce background noise

- **API errors**: 
  - Verify your API key is correct (for OpenAI)
  - Check your internet connection
  - Switch to Hugging Face free alternative or fallback mode
  - Hugging Face models may take time to load on first use

- **Audio issues**: 
  - Check your system's audio output settings
  - Ensure speakers/headphones are connected and not muted
  - Adjust `VOICE_VOLUME` in `.env` if too quiet/loud

- **pyaudio installation issues (Windows)**:
  ```bash
  pip install pipwin
  pipwin install pyaudio
  ```

## Requirements

- Python 3.8+
- Microphone
- Speakers/Headphones
- Internet connection (for speech recognition and API calls)

