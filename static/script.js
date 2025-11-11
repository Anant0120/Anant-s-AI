// Tabs and GIF-based voice state (using local mp.gif and sp.gif)
let currentTab = 'voice';

// Speech recognition and synthesis
let recognition = null;
let synth = window.speechSynthesis;

// State management
let isListening = false;
let isSpeaking = false;
let isPaused = false;
let isMuted = false;

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
	// New conversation
	const newBtn = document.getElementById('new-btn');
	if (newBtn) {
		newBtn.addEventListener('click', resetConversation);
	}
	
	function switchTab(tab) {
		currentTab = tab;
		if (tab === 'voice') {
			// ensure TTS is enabled on Voice tab
			isMuted = false;
			const muteBtnEl = document.getElementById('mute-btn');
			if (muteBtnEl) {
				muteBtnEl.classList.remove('active');
				muteBtnEl.title = 'Mute audio (TTS)';
			}
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

async function resetConversation() {
	// stop any ongoing speech
	if (synth) { try { synth.cancel(); } catch(e) {} }
	isSpeaking = false;
	isPaused = false;
	// clear chat UI
	const messagesContainer = document.getElementById('chat-messages');
	if (messagesContainer) messagesContainer.innerHTML = '';
	// reset server-side conversation
	try {
		await fetch('/api/reset', { method: 'POST' });
	} catch (e) {
		console.warn('Reset failed:', e);
	}
	// go back to Voice tab as default
	const tv = document.getElementById('tab-voice');
	if (tv) tv.click();
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
			if (vb) vb.style.display = 'none';
			break;
		case 'speaking':
			if (sp && img.src !== sp) img.src = sp;
			img.style.display = 'block';
			if (vb) vb.style.display = 'none';
			break;
		default:
			img.style.display = 'none';
			if (vb) vb.style.display = 'inline-flex';
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

	// If currently speaking, cancel so the user can ask mid-answer
	if (synth) { try { synth.cancel(); } catch(e) {} }
	isSpeaking = false;
	isPaused = false;
    
	// Remove any existing loading messages first
	const existingLoading = document.querySelector('.message .loading');
	if (existingLoading) {
		const loadingMsg = existingLoading.closest('.message');
		if (loadingMsg) loadingMsg.remove();
	}
    
	// Always append user message to chat history immediately (even if on Voice tab)
	addMessage(message, 'user');
    
    // Clear input
	const inputEl = document.getElementById('text-input');
	if (inputEl) inputEl.value = '';
    
    // Show loading indicator in chat tab
	const loadingId = currentTab === 'chat' ? addMessage('bot', true) : null;
    
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
			// Always append assistant message to chat
			addMessage(data.response, 'bot');
            speakText(data.response);
        } else {
			addMessage('Sorry, I encountered an error. Please try again.', 'bot');
        }
    } catch (error) {
        console.error('Error:', error);
		if (loadingId) removeMessage(loadingId);
		addMessage('Sorry, I encountered an error. Please try again.', 'bot');
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
	if (isMuted) {
		updateAnimation('idle');
		return;
	}
    
    // Stop any ongoing speech
    synth.cancel();

	// Clean markdown/symbols before speaking to avoid reading asterisks etc.
	const spokenText = sanitizeForSpeech(text);
    
    updateAnimation('speaking');
    isSpeaking = true;
	isPaused = false;
	// Show next control
	const nextBtn = document.getElementById('next-btn');
	if (nextBtn) { nextBtn.style.display = 'inline-flex'; }
    
    const utterance = new SpeechSynthesisUtterance(spokenText);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    
    utterance.onend = () => {
        isSpeaking = false;
        updateAnimation('idle');
		if (nextBtn) nextBtn.style.display = 'none';
    };
    
    utterance.onerror = () => {
        isSpeaking = false;
        updateAnimation('idle');
		if (nextBtn) nextBtn.style.display = 'none';
    };
    
    synth.speak(utterance);
}

// Remove basic markdown/markup so TTS doesn't speak symbols like * or `
function sanitizeForSpeech(input) {
	if (!input) return "";
	let t = String(input);
	// Convert markdown links [text](url) -> text
	t = t.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '$1');
	// Strip inline code/backticks
	t = t.replace(/`{1,3}([^`]+)`{1,3}/g, '$1');
	// Strip bold/italic asterisks or underscores ***text***, **text**, *text*, _text_
	t = t.replace(/\*{1,3}([^*]+)\*{1,3}/g, '$1').replace(/_{1,3}([^_]+)_{1,3}/g, '$1');
	// Remove remaining markdown bullets and headers at line starts
	t = t.replace(/^\s*[-*+#>]\s+/gm, '');
	// Collapse multiple spaces/newlines
	t = t.replace(/[ \t]{2,}/g, ' ').replace(/\n{2,}/g, '\n').trim();
	return t;
}
// Event listeners
document.addEventListener('DOMContentLoaded', () => {
	initUI();
    initSpeechRecognition();
	// Ensure the voice GIF is hidden until listening/speaking
	updateAnimation('idle');
    
	// Voice button
	document.getElementById('voice-btn').addEventListener('click', () => {
		// barge-in during speaking
		if (isSpeaking && synth) {
			try { synth.cancel(); } catch(e) {}
			isSpeaking = false;
			isPaused = false;
		}
		if (isListening) {
			recognition.stop();
		} else {
			recognition.start();
		}
	});

	// Skip current speech and immediately listen
	const nextBtn = document.getElementById('next-btn');
	if (nextBtn) {
		nextBtn.addEventListener('click', () => {
			if (synth) { try { synth.cancel(); } catch(e) {} }
			isSpeaking = false;
			isPaused = false;
			updateAnimation('listening');
			recognition.start();
		});
	}

	// Mute/Unmute TTS on Chat
	const muteBtn = document.getElementById('mute-btn');
	if (muteBtn) {
		muteBtn.addEventListener('click', () => {
			isMuted = !isMuted;
			if (isMuted && synth) { try { synth.cancel(); } catch(e) {} }
			muteBtn.classList.toggle('active', isMuted);
			muteBtn.title = isMuted ? 'Unmute audio (TTS)' : 'Mute audio (TTS)';
		});
	}
    
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

