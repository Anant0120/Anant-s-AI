// Tabs and GIF-based voice state (using local mp.gif and sp.gif)
let currentTab = 'voice';

// Speech recognition and synthesis
let recognition = null;
let synth = window.speechSynthesis;

// State management
let isListening = false;
let isSpeaking = false;

// Initialize UI
async function initUI() {
	// Preload GIFs to avoid flicker
	preloadVoiceGifs();

	// Tabs
	const tabVoice = document.getElementById('tab-voice');
	const tabChat = document.getElementById('tab-chat');
	const voicePane = document.getElementById('voice-pane');
	const chatPane = document.getElementById('chat-pane');
	
	tabVoice.addEventListener('click', () => switchTab('voice'));
	tabChat.addEventListener('click', () => switchTab('chat'));
	
	function switchTab(tab) {
		currentTab = tab;
		if (tab === 'voice') {
			tabVoice.classList.add('active');
			tabChat.classList.remove('active');
			voicePane.classList.add('active');
			chatPane.classList.remove('active');
		} else {
			tabChat.classList.add('active');
			tabVoice.classList.remove('active');
			chatPane.classList.add('active');
			voicePane.classList.remove('active');
		}
	}
}

function preloadVoiceGifs() {
	const imgEl = document.getElementById('voice-gif');
	if (!imgEl) return;
	const mp = imgEl.getAttribute('data-mp');
	const sp = imgEl.getAttribute('data-sp');
	if (mp) {
		const i1 = new Image();
		i1.src = mp;
	}
	if (sp) {
		const i2 = new Image();
		i2.src = sp;
	}
	// Prevent drag/select artifacts
	imgEl.draggable = false;
}

// Update "animation" (now GIF) based on state
async function updateAnimation(state) {
	const img = document.getElementById('voice-gif');
	const vb = document.getElementById('voice-btn');
	if (!img) return;
	const mp = img.getAttribute('data-mp');
	const sp = img.getAttribute('data-sp');
	switch(state) {
		case 'listening':
			if (mp && img.src !== mp) img.src = mp;
			img.style.display = 'block';
			if (vb) vb.style.visibility = 'hidden';
			if (vb) vb.style.pointerEvents = 'none';
			break;
		case 'speaking':
			if (sp && img.src !== sp) img.src = sp;
			img.style.display = 'block';
			if (vb) vb.style.visibility = 'hidden';
			if (vb) vb.style.pointerEvents = 'none';
			break;
		default:
			img.style.display = 'none';
			if (vb) vb.style.visibility = 'visible';
			if (vb) vb.style.pointerEvents = 'auto';
			break;
	}
}

// Initialize speech recognition
function initSpeechRecognition() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';
        
        recognition.onstart = () => {
            isListening = true;
            updateAnimation('listening');
			const vb = document.getElementById('voice-btn');
			if (vb) vb.classList.add('listening');
        };
        
        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            recognition.stop();
            sendMessage(transcript);
        };
        
        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            isListening = false;
            updateAnimation('idle');
			const vb = document.getElementById('voice-btn');
			if (vb) vb.classList.remove('listening');
        };
        
        recognition.onend = () => {
            isListening = false;
            if (!isSpeaking) {
                updateAnimation('idle');
            }
			const vb = document.getElementById('voice-btn');
			if (vb) vb.classList.remove('listening');
        };
    } else {
        console.warn('Speech recognition not supported');
		const vb = document.getElementById('voice-btn');
		if (vb) vb.style.display = 'none';
    }
}

// Send message to API
async function sendMessage(message) {
    if (!message.trim()) return;
    
	// Add user message only if in chat tab
	if (currentTab === 'chat') {
		addMessage(message, 'user');
	}
    
    // Clear input
	const inputEl = document.getElementById('text-input');
	if (inputEl) inputEl.value = '';
    
    // Show loading
	const loadingId = currentTab === 'chat' ? addMessage('Thinking...', 'bot', true) : null;
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ question: message })
        });
        
        const data = await response.json();
        
        // Remove loading message
		if (loadingId) removeMessage(loadingId);
        
        if (data.success) {
			if (currentTab === 'chat') {
				addMessage(data.response, 'bot');
			}
            speakText(data.response);
        } else {
			if (currentTab === 'chat') {
				addMessage('Sorry, I encountered an error. Please try again.', 'bot');
			}
        }
    } catch (error) {
        console.error('Error:', error);
		if (loadingId) removeMessage(loadingId);
		if (currentTab === 'chat') {
			addMessage('Sorry, I encountered an error. Please try again.', 'bot');
		}
    }
}

// Add message to chat
function addMessage(text, type, isLoading = false) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    const messageId = 'msg-' + Date.now();
    messageDiv.id = messageId;
    messageDiv.className = `message ${type}-message`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    if (isLoading) {
        contentDiv.innerHTML = `<span class="loading">${text}</span>`;
    } else {
        contentDiv.textContent = text;
    }
    
    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);
    
    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    return messageId;
}

// Remove message
function removeMessage(messageId) {
    const message = document.getElementById(messageId);
    if (message) {
        message.remove();
    }
}

// Speak text using Web Speech API
function speakText(text) {
    if (!synth) return;
    
    // Stop any ongoing speech
    synth.cancel();
    
    updateAnimation('speaking');
    isSpeaking = true;
    
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    
    utterance.onend = () => {
        isSpeaking = false;
        updateAnimation('idle');
    };
    
    utterance.onerror = () => {
        isSpeaking = false;
        updateAnimation('idle');
    };
    
    synth.speak(utterance);
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
	initUI();
    initSpeechRecognition();
	// Ensure the voice GIF is hidden until listening/speaking
	updateAnimation('idle');
    
    // Voice button
    document.getElementById('voice-btn').addEventListener('click', () => {
        if (isListening) {
            recognition.stop();
        } else {
            recognition.start();
        }
    });
    
    // Send button
    document.getElementById('send-btn').addEventListener('click', () => {
        const input = document.getElementById('text-input');
        sendMessage(input.value);
    });
    
    // Enter key in input
    document.getElementById('text-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage(e.target.value);
        }
    });
});

