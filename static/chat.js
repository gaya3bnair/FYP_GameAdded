// // ========== State ==========
// let currentUser = null;
// let isSignupMode = false;

// // ========== DOM Elements ==========
// const authContainer = document.getElementById('authContainer');
// const chatbox = document.getElementById('chatbox');
// const signinForm = document.getElementById('signinForm');
// const signupForm = document.getElementById('signupForm');
// const toggleLink = document.getElementById('toggleLink');
// const toggleText = document.getElementById('toggleText');
// const authTitle = document.getElementById('authTitle');
// const errorMessage = document.getElementById('errorMessage');
// const successMessage = document.getElementById('successMessage');
// const userName = document.getElementById('userName');
// const messagesDiv = document.getElementById('messages');
// const queryInput = document.getElementById('query');
// const fileInput = document.getElementById('fileInput');
// const uploadForm = document.getElementById('uploadForm');
// const voiceLangSelect = document.getElementById('voiceLangSelect');

// /** Set when the message was sent from the mic; cleared after send (for server logs / future use). */
// let pendingVoiceLocale = null;

// // ========== Utility Functions ==========
// function showError(message) {
//     errorMessage.textContent = message;
//     errorMessage.style.display = 'block';
//     successMessage.style.display = 'none';
// }

// function showSuccess(message) {
//     successMessage.textContent = message;
//     successMessage.style.display = 'block';
//     errorMessage.style.display = 'none';
// }

// function hideMessages() {
//     errorMessage.style.display = 'none';
//     successMessage.style.display = 'none';
// }

// function escapeHtml(text) {
//     const div = document.createElement('div');
//     div.textContent = text;
//     return div.innerHTML;
// }

// // ========== Auth Functions ==========
// async function checkAuth() {
//     try {
//         const res = await fetch('/me');
//         const data = await res.json();
        
//         if (data.authenticated) {
//             currentUser = data;
//             showChat();
//             loadChatHistory();
//         } else {
//             showAuth();
//         }
//     } catch (err) {
//         console.error('Auth check failed:', err);
//         showAuth();
//     }
// }

// function showAuth() {
//     authContainer.style.display = 'block';
//     chatbox.style.display = 'none';
// }

// function showChat() {
//     authContainer.style.display = 'none';
//     chatbox.style.display = 'flex';
//     userName.textContent = currentUser.name || currentUser.email;
// }

// toggleLink.addEventListener('click', () => {
//     isSignupMode = !isSignupMode;
//     hideMessages();
    
//     if (isSignupMode) {
//         signinForm.classList.add('hidden');
//         signupForm.classList.remove('hidden');
//         authTitle.textContent = 'Sign Up';
//         toggleText.textContent = 'Already have an account?';
//         toggleLink.textContent = 'Sign In';
//     } else {
//         signupForm.classList.add('hidden');
//         signinForm.classList.remove('hidden');
//         authTitle.textContent = 'Sign In';
//         toggleText.textContent = "Don't have an account?";
//         toggleLink.textContent = 'Sign Up';
//     }
// });

// signinForm.addEventListener('submit', async (e) => {
//     e.preventDefault();
//     hideMessages();
    
//     const email = document.getElementById('signinEmail').value;
//     const password = document.getElementById('signinPassword').value;
    
//     try {
//         const res = await fetch('/signin', {
//             method: 'POST',
//             headers: {'Content-Type': 'application/json'},
//             body: JSON.stringify({email, password})
//         });
        
//         const data = await res.json();
        
//         if (res.ok) {
//             currentUser = data;
//             showChat();
//             loadChatHistory();
//         } else {
//             showError(data.error || 'Sign in failed');
//         }
//     } catch (err) {
//         showError('Connection error. Please try again.');
//     }
// });

// signupForm.addEventListener('submit', async (e) => {
//     e.preventDefault();
//     hideMessages();
    
//     const name = document.getElementById('signupName').value;
//     const email = document.getElementById('signupEmail').value;
//     const password = document.getElementById('signupPassword').value;
    
//     try {
//         const res = await fetch('/signup', {
//             method: 'POST',
//             headers: {'Content-Type': 'application/json'},
//             body: JSON.stringify({name, email, password})
//         });
        
//         const data = await res.json();
        
//         if (res.ok) {
//             showSuccess('Account created! Please sign in.');
//             setTimeout(() => {
//                 toggleLink.click(); // Switch to sign in form
//             }, 1500);
//         } else {
//             showError(data.error || 'Sign up failed');
//         }
//     } catch (err) {
//         showError('Connection error. Please try again.');
//     }
// });

// async function signOut() {
//     try {
//         await fetch('/signout', {method: 'POST'});
//         currentUser = null;
//         messagesDiv.innerHTML = '<div class="empty-state"><p>No messages yet. Upload a document and start chatting!</p></div>';
//         showAuth();
//     } catch (err) {
//         console.error('Sign out error:', err);
//     }
// }

// function renderFeedback(messageId, query, response, container, emotion = "neutral") {
//     if (!messageId) return;
 
//     const bar = document.createElement("div");
//     bar.className = "feedback-bar";
 
//     const thumbUp   = document.createElement("button");
//     thumbUp.className   = "feedback-btn";
//     thumbUp.textContent = "👍";
//     thumbUp.title       = "Good response";
 
//     const thumbDown = document.createElement("button");
//     thumbDown.className   = "feedback-btn";
//     thumbDown.textContent = "👎";
//     thumbDown.title       = "Bad response";
 
//     const thanks = document.createElement("span");
//     thanks.className    = "feedback-thanks";
//     thanks.style.display = "none";
//     thanks.textContent  = "Thanks for your feedback!";
 
//     bar.appendChild(thumbUp);
//     bar.appendChild(thumbDown);
//     bar.appendChild(thanks);
//     container.appendChild(bar);
 
//     async function submitFeedback(rating) {
//         thumbUp.disabled  = true;
//         thumbDown.disabled = true;
 
//         if (rating === 1) thumbUp.classList.add("selected-up");
//         else              thumbDown.classList.add("selected-down");
 
//         thanks.style.display = "inline";
 
//         try {
//             const res = await fetch("/feedback", {
//                 method: "POST",
//                 headers: { "Content-Type": "application/json" },
//                 body: JSON.stringify({
//                     message_id: messageId,
//                     query:      query,
//                     response:   response,
//                     rating:     rating,
//                     emotion:    emotion,    // ← EARS: emotion sent with feedback
//                 }),
//             });
//             if (!res.ok) thanks.textContent = "Could not save feedback.";
//         } catch (err) {
//             thanks.textContent = "Could not save feedback.";
//         }
//     }
 
//     thumbUp.addEventListener("click",  () => submitFeedback(1));
//     thumbDown.addEventListener("click", () => submitFeedback(0));
// }
// // ========== Voice to Text (Web Speech API) ==========
// // The server translates Malayalam using sarvam_utils; use ml-IN here so Malayalam speech is transcribed in Malayalam script.

// const voiceBtn = document.getElementById('voiceBtn');

// const SpeechRecognition =
//     typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition);

// let recognition;
// if (SpeechRecognition) {
//     recognition = new SpeechRecognition();
//     if (voiceLangSelect) {
//         voiceLangSelect.value = localStorage.getItem('voiceLang') || 'en-US';
//         recognition.lang = voiceLangSelect.value;
//         voiceLangSelect.addEventListener('change', () => {
//             localStorage.setItem('voiceLang', voiceLangSelect.value);
//             recognition.lang = voiceLangSelect.value;
//         });
//     } else {
//         recognition.lang = 'en-US';
//     }
//     recognition.continuous = false;
//     recognition.interimResults = false;

//     recognition.onstart = () => {
//         voiceBtn.classList.add("listening");
//         voiceBtn.textContent = "🎙️ Listening...";
//     };

//     recognition.onend = () => {
//         voiceBtn.classList.remove("listening");
//         voiceBtn.textContent = "🎤";
//     };

//     recognition.onresult = (event) => {
//         const speechText = event.results[0][0].transcript;
//         console.log("Voice Input:", speechText);

//         queryInput.value = speechText;
//         if (voiceLangSelect) {
//             pendingVoiceLocale = voiceLangSelect.value;
//         }
//         sendMessage();
//     };
// }

// voiceBtn.addEventListener("click", () => {
//     if (!recognition) {
//         alert("Your browser does not support voice input.");
//         return;
//     }
//     if (voiceLangSelect) {
//         recognition.lang = voiceLangSelect.value;
//     }
//     try {
//         recognition.start();
//     } catch (err) {
//         console.error("Speech recognition:", err);
//     }
// });

// // ========== Chat Functions ==========
// async function loadChatHistory() {
//     try {
//         const res = await fetch('/history');
//         const data = await res.json();
        
//         if (data.history && data.history.length > 0) {
//             messagesDiv.innerHTML = '';
//             data.history.forEach(msg => {
//                 appendMessage(msg.role, msg.message);
//             });
//         }
//     } catch (err) {
//         console.error('Failed to load history:', err);
//     }
// }

// function appendMessage(role, text) {
//     const emptyState = messagesDiv.querySelector('.empty-state');
//     if (emptyState) emptyState.remove();
    
//     const msgDiv = document.createElement('div');
//     msgDiv.className = `msg ${role}`;
    
//     const contentDiv = document.createElement('div');
//     contentDiv.className = 'msg-content';
//     contentDiv.innerHTML = `<strong>${role === 'user' ? 'You' : 'Bot'}:</strong> ${escapeHtml(text)}`;
    
//     msgDiv.appendChild(contentDiv);
//     messagesDiv.appendChild(msgDiv);
//     messagesDiv.scrollTop = messagesDiv.scrollHeight;
// }

// async function sendMessage() {
//     const query = queryInput.value.trim();
//     if (!query) return;

//     const voiceLocale = pendingVoiceLocale;
//     pendingVoiceLocale = null;

//     appendMessage('user', query);
//     queryInput.value = '';

//     const typing = document.createElement('div');
//     typing.className = 'msg bot';
//     typing.innerHTML = `<div class='msg-content'><em>Typing...</em></div>`;
//     messagesDiv.appendChild(typing);
//     messagesDiv.scrollTop = messagesDiv.scrollHeight;

//     const payload = { query };
//     if (voiceLocale) {
//         payload.voice_locale = voiceLocale;
//     }

//     try {
//         const res = await fetch('/chat', {
//             method: 'POST',
//             headers: {'Content-Type': 'application/json'},
//             body: JSON.stringify(payload)
//         });
        
//         const data = await res.json();
//         typing.remove();
        
//         if (res.ok) {
//             // appendMessage('bot', data.response);
//             appendMessage('bot', data.response, data.message_id, query, data.emotion || 'neutral');
//         } else {
//             appendMessage('bot', `❌ Error: ${data.error || 'Unknown error'}`);
//         }
//     } catch (err) {
//         typing.remove();
//         appendMessage('bot', '❌ Error connecting to server.');
//     }
// }

// // Handle Enter key
// queryInput.addEventListener('keypress', (e) => {
//     if (e.key === 'Enter') sendMessage();
// });

// // File upload
// fileInput.addEventListener('change', (e) => {
//     const fileName = e.target.files[0]?.name || 'Choose a file to upload...';
//     document.getElementById('fileName').textContent = fileName;
// });

// uploadForm.addEventListener('submit', async (e) => {
//     e.preventDefault();
    
//     const file = fileInput.files[0];
//     if (!file) {
//         alert('Please select a file first');
//         return;
//     }
    
//     const formData = new FormData();
//     formData.append('file', file);
    
//     const fileName = document.getElementById('fileName');
//     fileName.textContent = 'Uploading...';
    
//     try {
//         const res = await fetch('/upload', {
//             method: 'POST',
//             body: formData
//         });
        
//         const data = await res.json();
        
//         if (res.ok) {
//             fileName.textContent = 'Upload successful! ✓';
//             appendMessage('bot', `📄 ${data.message}`);
//             setTimeout(() => {
//                 fileName.textContent = 'Choose a file to upload...';
//                 fileInput.value = '';
//             }, 2000);
//         } else {
//             fileName.textContent = 'Upload failed ✗';
//             appendMessage('bot', `❌ Upload error: ${data.error}`);
//         }
//     } catch (err) {
//         fileName.textContent = 'Upload failed ✗';
//         appendMessage('bot', '❌ Upload failed: Connection error');
//     }
// });

// // ========== Initialize ==========
// checkAuth();




// // ========== State ==========
// let currentUser      = null;
// let isSignupMode     = false;
// let lastUserQuery    = '';   // tracks last typed query for feedback
// let lastUserEmotion  = 'neutral'; // tracks last emotion for feedback

// // ========== DOM Elements ==========
// const authContainer  = document.getElementById('authContainer');
// const chatbox        = document.getElementById('chatbox');
// const signinForm     = document.getElementById('signinForm');
// const signupForm     = document.getElementById('signupForm');
// const toggleLink     = document.getElementById('toggleLink');
// const toggleText     = document.getElementById('toggleText');
// const authTitle      = document.getElementById('authTitle');
// const errorMessage   = document.getElementById('errorMessage');
// const successMessage = document.getElementById('successMessage');
// const userName       = document.getElementById('userName');
// const messagesDiv    = document.getElementById('messages');
// const queryInput     = document.getElementById('query');
// const fileInput      = document.getElementById('fileInput');
// const uploadForm     = document.getElementById('uploadForm');
// const voiceLangSelect = document.getElementById('voiceLangSelect');

// /** Set when message sent from mic; cleared after send. */
// let pendingVoiceLocale = null;

// // ========== Utility ==========
// function showError(message) {
//     errorMessage.textContent = message;
//     errorMessage.style.display = 'block';
//     successMessage.style.display = 'none';
// }

// function showSuccess(message) {
//     successMessage.textContent = message;
//     successMessage.style.display = 'block';
//     errorMessage.style.display = 'none';
// }

// function hideMessages() {
//     errorMessage.style.display = 'none';
//     successMessage.style.display = 'none';
// }

// function escapeHtml(text) {
//     const div = document.createElement('div');
//     div.textContent = text;
//     return div.innerHTML;
// }

// // ========== EARS Feedback ==========
// /**
//  * Renders 👍/👎 feedback bar below bot messages.
//  * Sends emotion alongside rating so EARS can train emotion-conditioned reward.
//  *
//  * @param {string}  messageId  - UUID from backend
//  * @param {string}  query      - User's original message
//  * @param {string}  response   - Bot's response text
//  * @param {Element} container  - DOM element to append bar to
//  * @param {string}  emotion    - Detected emotion ('sad','happy','neutral', etc.)
//  */
// function renderFeedback(messageId, query, response, container, emotion = "neutral") {
//     if (!messageId) return;

//     const bar = document.createElement("div");
//     bar.className = "feedback-bar";

//     const thumbUp = document.createElement("button");
//     thumbUp.className   = "feedback-btn";
//     thumbUp.textContent = "👍";
//     thumbUp.title       = "Good response";

//     const thumbDown = document.createElement("button");
//     thumbDown.className   = "feedback-btn";
//     thumbDown.textContent = "👎";
//     thumbDown.title       = "Bad response";

//     const thanks = document.createElement("span");
//     thanks.className     = "feedback-thanks";
//     thanks.style.display = "none";
//     thanks.textContent   = "Thanks for your feedback!";

//     bar.appendChild(thumbUp);
//     bar.appendChild(thumbDown);
//     bar.appendChild(thanks);
//     container.appendChild(bar);

//     async function submitFeedback(rating) {
//         thumbUp.disabled  = true;
//         thumbDown.disabled = true;

//         if (rating === 1) thumbUp.classList.add("selected-up");
//         else              thumbDown.classList.add("selected-down");

//         thanks.style.display = "inline";

//         try {
//             const res = await fetch("/feedback", {
//                 method:  "POST",
//                 headers: { "Content-Type": "application/json" },
//                 body: JSON.stringify({
//                     message_id: messageId,
//                     query:      query,
//                     response:   response,
//                     rating:     rating,
//                     emotion:    emotion,   // ← EARS: emotion sent with every rating
//                 }),
//             });
//             if (!res.ok) thanks.textContent = "Could not save feedback.";
//         } catch (err) {
//             thanks.textContent = "Could not save feedback.";
//         }
//     }

//     thumbUp.addEventListener("click",  () => submitFeedback(1));
//     thumbDown.addEventListener("click", () => submitFeedback(0));
// }

// // ========== Auth ==========
// async function checkAuth() {
//     try {
//         const res  = await fetch('/me');
//         const data = await res.json();
//         if (data.authenticated) {
//             currentUser = data;
//             showChat();
//             loadChatHistory();
//         } else {
//             showAuth();
//         }
//     } catch (err) {
//         console.error('Auth check failed:', err);
//         showAuth();
//     }
// }

// function showAuth() {
//     authContainer.style.display = 'block';
//     chatbox.style.display       = 'none';
// }

// function showChat() {
//     authContainer.style.display = 'none';
//     chatbox.style.display       = 'flex';
//     userName.textContent        = currentUser.name || currentUser.email;
// }

// toggleLink.addEventListener('click', () => {
//     isSignupMode = !isSignupMode;
//     hideMessages();
//     if (isSignupMode) {
//         signinForm.classList.add('hidden');
//         signupForm.classList.remove('hidden');
//         authTitle.textContent   = 'Sign Up';
//         toggleText.textContent  = 'Already have an account?';
//         toggleLink.textContent  = 'Sign In';
//     } else {
//         signupForm.classList.add('hidden');
//         signinForm.classList.remove('hidden');
//         authTitle.textContent   = 'Sign In';
//         toggleText.textContent  = "Don't have an account?";
//         toggleLink.textContent  = 'Sign Up';
//     }
// });

// signinForm.addEventListener('submit', async (e) => {
//     e.preventDefault();
//     hideMessages();
//     const email    = document.getElementById('signinEmail').value;
//     const password = document.getElementById('signinPassword').value;
//     try {
//         const res  = await fetch('/signin', {
//             method:  'POST',
//             headers: { 'Content-Type': 'application/json' },
//             body:    JSON.stringify({ email, password })
//         });
//         const data = await res.json();
//         if (res.ok) {
//             currentUser = data;
//             showChat();
//             loadChatHistory();
//         } else {
//             showError(data.error || 'Sign in failed');
//         }
//     } catch (err) {
//         showError('Connection error. Please try again.');
//     }
// });

// signupForm.addEventListener('submit', async (e) => {
//     e.preventDefault();
//     hideMessages();
//     const name     = document.getElementById('signupName').value;
//     const email    = document.getElementById('signupEmail').value;
//     const password = document.getElementById('signupPassword').value;
//     try {
//         const res  = await fetch('/signup', {
//             method:  'POST',
//             headers: { 'Content-Type': 'application/json' },
//             body:    JSON.stringify({ name, email, password })
//         });
//         const data = await res.json();
//         if (res.ok) {
//             showSuccess('Account created! Please sign in.');
//             setTimeout(() => toggleLink.click(), 1500);
//         } else {
//             showError(data.error || 'Sign up failed');
//         }
//     } catch (err) {
//         showError('Connection error. Please try again.');
//     }
// });

// async function signOut() {
//     try {
//         await fetch('/signout', { method: 'POST' });
//         currentUser  = null;
//         messagesDiv.innerHTML = '<div class="empty-state"><p>No messages yet. Upload a document and start chatting!</p></div>';
//         showAuth();
//     } catch (err) {
//         console.error('Sign out error:', err);
//     }
// }

// // ========== Voice (Web Speech API) ==========
// const voiceBtn = document.getElementById('voiceBtn');

// const SpeechRecognition =
//     typeof window !== 'undefined' &&
//     (window.SpeechRecognition || window.webkitSpeechRecognition);

// let recognition;
// if (SpeechRecognition) {
//     recognition = new SpeechRecognition();
//     if (voiceLangSelect) {
//         voiceLangSelect.value = localStorage.getItem('voiceLang') || 'en-US';
//         recognition.lang      = voiceLangSelect.value;
//         voiceLangSelect.addEventListener('change', () => {
//             localStorage.setItem('voiceLang', voiceLangSelect.value);
//             recognition.lang = voiceLangSelect.value;
//         });
//     } else {
//         recognition.lang = 'en-US';
//     }
//     recognition.continuous     = false;
//     recognition.interimResults = false;

//     recognition.onstart = () => {
//         voiceBtn.classList.add("listening");
//         voiceBtn.textContent = "🎙️ Listening...";
//     };

//     recognition.onend = () => {
//         voiceBtn.classList.remove("listening");
//         voiceBtn.textContent = "🎤";
//     };

//     recognition.onresult = (event) => {
//         const speechText = event.results[0][0].transcript;
//         console.log("Voice Input:", speechText);
//         queryInput.value = speechText;
//         if (voiceLangSelect) pendingVoiceLocale = voiceLangSelect.value;
//         sendMessage();
//     };
// }

// voiceBtn.addEventListener("click", () => {
//     if (!recognition) {
//         alert("Your browser does not support voice input.");
//         return;
//     }
//     if (voiceLangSelect) recognition.lang = voiceLangSelect.value;
//     try {
//         recognition.start();
//     } catch (err) {
//         console.error("Speech recognition:", err);
//     }
// });

// // ========== Chat ==========
// async function loadChatHistory() {
//     try {
//         const res  = await fetch('/history');
//         const data = await res.json();
//         if (data.history && data.history.length > 0) {
//             messagesDiv.innerHTML = '';
//             data.history.forEach(msg => {
//                 // History messages have no message_id — no feedback bar shown
//                 appendMessage(msg.role, msg.message);
//             });
//         }
//     } catch (err) {
//         console.error('Failed to load history:', err);
//     }
// }

// /**
//  * Creates and appends a message bubble.
//  * Bot messages with a messageId get a feedback bar with emotion attached.
//  *
//  * @param {string}  role       - 'user' or 'bot'
//  * @param {string}  text       - message content
//  * @param {string}  messageId  - UUID from backend (bot messages only)
//  * @param {string}  query      - original user query (for feedback payload)
//  * @param {string}  emotion    - detected emotion (for EARS feedback payload)
//  */
// function appendMessage(role, text, messageId = null, query = null, emotion = "neutral") {
//     const emptyState = messagesDiv.querySelector('.empty-state');
//     if (emptyState) emptyState.remove();

//     const msgDiv = document.createElement('div');
//     msgDiv.className = `msg ${role}`;

//     const contentDiv = document.createElement('div');
//     contentDiv.className = 'msg-content';
//     contentDiv.innerHTML = `<strong>${role === 'user' ? 'You' : 'Bot'}:</strong> ${escapeHtml(text)}`;

//     msgDiv.appendChild(contentDiv);

//     // Add EARS feedback bar for bot messages that have a messageId
//     if (role === 'bot' && messageId) {
//         const feedbackQuery   = query || lastUserQuery;
//         const feedbackEmotion = emotion || lastUserEmotion;
//         renderFeedback(messageId, feedbackQuery, text, msgDiv, feedbackEmotion);
//     }

//     messagesDiv.appendChild(msgDiv);
//     messagesDiv.scrollTop = messagesDiv.scrollHeight;
// }

// async function sendMessage() {
//     const query = queryInput.value.trim();
//     if (!query) return;

//     const voiceLocale = pendingVoiceLocale;
//     pendingVoiceLocale = null;

//     lastUserQuery = query;   // store for feedback reference

//     appendMessage('user', query);
//     queryInput.value = '';

//     const typing = document.createElement('div');
//     typing.className = 'msg bot';
//     typing.innerHTML = `<div class='msg-content'><em>Typing...</em></div>`;
//     messagesDiv.appendChild(typing);
//     messagesDiv.scrollTop = messagesDiv.scrollHeight;

//     const payload = { query };
//     if (voiceLocale) payload.voice_locale = voiceLocale;

//     try {
//         const res  = await fetch('/chat', {
//             method:  'POST',
//             headers: { 'Content-Type': 'application/json' },
//             body:    JSON.stringify(payload)
//         });
//         const data = await res.json();
//         typing.remove();

//         if (res.ok) {
//             const emotion = data.emotion || 'neutral';
//             lastUserEmotion = emotion;
//             // Pass message_id, query and emotion for EARS feedback bar
//             appendMessage('bot', data.response, data.message_id, query, emotion);
//         } else {
//             appendMessage('bot', `❌ Error: ${data.error || 'Unknown error'}`);
//         }
//     } catch (err) {
//         typing.remove();
//         appendMessage('bot', '❌ Error connecting to server.');
//     }
// }

// // Enter key
// queryInput.addEventListener('keypress', (e) => {
//     if (e.key === 'Enter') sendMessage();
// });

// // File upload
// fileInput.addEventListener('change', (e) => {
//     const fileName = e.target.files[0]?.name || 'Choose a file to upload...';
//     document.getElementById('fileName').textContent = fileName;
// });

// uploadForm.addEventListener('submit', async (e) => {
//     e.preventDefault();
//     const file = fileInput.files[0];
//     if (!file) { alert('Please select a file first'); return; }

//     const formData = new FormData();
//     formData.append('file', file);
//     const fileName = document.getElementById('fileName');
//     fileName.textContent = 'Uploading...';

//     try {
//         const res  = await fetch('/upload', { method: 'POST', body: formData });
//         const data = await res.json();
//         if (res.ok) {
//             fileName.textContent = 'Upload successful! ✓';
//             appendMessage('bot', `📄 ${data.message}`);
//             setTimeout(() => {
//                 fileName.textContent = 'Choose a file to upload...';
//                 fileInput.value = '';
//             }, 2000);
//         } else {
//             fileName.textContent = 'Upload failed ✗';
//             appendMessage('bot', `❌ Upload error: ${data.error}`);
//         }
//     } catch (err) {
//         fileName.textContent = 'Upload failed ✗';
//         appendMessage('bot', '❌ Upload failed: Connection error');
//     }
// });

// // ========== Initialize ==========
// checkAuth();

// ========== State ==========
let currentUser      = null;
let isSignupMode     = false;
let lastUserQuery    = '';
let lastUserEmotion  = 'neutral';

// ========== DOM Elements ==========
const authContainer  = document.getElementById('authContainer');
const chatbox        = document.getElementById('chatbox');
const signinForm     = document.getElementById('signinForm');
const signupForm     = document.getElementById('signupForm');
const toggleLink     = document.getElementById('toggleLink');
const toggleText     = document.getElementById('toggleText');
const authTitle      = document.getElementById('authTitle');
const errorMessage   = document.getElementById('errorMessage');
const successMessage = document.getElementById('successMessage');
const userName       = document.getElementById('userName');
const messagesDiv    = document.getElementById('messages');
const queryInput     = document.getElementById('query');
const fileInput      = document.getElementById('fileInput');
const uploadForm     = document.getElementById('uploadForm');
const voiceBtn       = document.getElementById('voiceBtn');

// ========== Utility ==========
function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    successMessage.style.display = 'none';
}

function showSuccess(message) {
    successMessage.textContent = message;
    successMessage.style.display = 'block';
    errorMessage.style.display = 'none';
}

function hideMessages() {
    errorMessage.style.display = 'none';
    successMessage.style.display = 'none';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ========== EARS Feedback ==========
function renderFeedback(messageId, query, response, container, emotion = "neutral") {
    if (!messageId) return;

    const bar = document.createElement("div");
    bar.className = "feedback-bar";

    const thumbUp = document.createElement("button");
    thumbUp.className   = "feedback-btn";
    thumbUp.textContent = "👍";
    thumbUp.title       = "Good response";

    const thumbDown = document.createElement("button");
    thumbDown.className   = "feedback-btn";
    thumbDown.textContent = "👎";
    thumbDown.title       = "Bad response";

    const thanks = document.createElement("span");
    thanks.className     = "feedback-thanks";
    thanks.style.display = "none";
    thanks.textContent   = "Thanks for your feedback!";

    bar.appendChild(thumbUp);
    bar.appendChild(thumbDown);
    bar.appendChild(thanks);
    container.appendChild(bar);

    async function submitFeedback(rating) {
        thumbUp.disabled   = true;
        thumbDown.disabled = true;

        if (rating === 1) thumbUp.classList.add("selected-up");
        else              thumbDown.classList.add("selected-down");

        thanks.style.display = "inline";

        try {
            const res = await fetch("/feedback", {
                method:  "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message_id: messageId,
                    query:      query,
                    response:   response,
                    rating:     rating,
                    emotion:    emotion,
                }),
            });
            if (!res.ok) thanks.textContent = "Could not save feedback.";
        } catch (err) {
            thanks.textContent = "Could not save feedback.";
        }
    }

    thumbUp.addEventListener("click",  () => submitFeedback(1));
    thumbDown.addEventListener("click", () => submitFeedback(0));
}

// ========== Auth ==========
async function checkAuth() {
    try {
        const res  = await fetch('/me');
        const data = await res.json();
        if (data.authenticated) {
            currentUser = data;
            showChat();
            loadChatHistory();
        } else {
            showAuth();
        }
    } catch (err) {
        console.error('Auth check failed:', err);
        showAuth();
    }
}

function showAuth() {
    authContainer.style.display = 'block';
    chatbox.style.display       = 'none';
}

function showChat() {
    authContainer.style.display = 'none';
    chatbox.style.display       = 'flex';
    userName.textContent        = currentUser.name || currentUser.email;
}

toggleLink.addEventListener('click', () => {
    isSignupMode = !isSignupMode;
    hideMessages();
    if (isSignupMode) {
        signinForm.classList.add('hidden');
        signupForm.classList.remove('hidden');
        authTitle.textContent  = 'Sign Up';
        toggleText.textContent = 'Already have an account?';
        toggleLink.textContent = 'Sign In';
    } else {
        signupForm.classList.add('hidden');
        signinForm.classList.remove('hidden');
        authTitle.textContent  = 'Sign In';
        toggleText.textContent = "Don't have an account?";
        toggleLink.textContent = 'Sign Up';
    }
});

signinForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideMessages();
    const email    = document.getElementById('signinEmail').value;
    const password = document.getElementById('signinPassword').value;
    try {
        const res  = await fetch('/signin', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (res.ok) { currentUser = data; showChat(); loadChatHistory(); }
        else showError(data.error || 'Sign in failed');
    } catch (err) { showError('Connection error. Please try again.'); }
});

signupForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideMessages();
    const name     = document.getElementById('signupName').value;
    const email    = document.getElementById('signupEmail').value;
    const password = document.getElementById('signupPassword').value;
    try {
        const res  = await fetch('/signup', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password })
        });
        const data = await res.json();
        if (res.ok) { showSuccess('Account created! Please sign in.'); setTimeout(() => toggleLink.click(), 1500); }
        else showError(data.error || 'Sign up failed');
    } catch (err) { showError('Connection error. Please try again.'); }
});

async function signOut() {
    try {
        await fetch('/signout', { method: 'POST' });
        currentUser = null;
        messagesDiv.innerHTML = '<div class="empty-state"><p>No messages yet. Upload a document and start chatting!</p></div>';
        showAuth();
    } catch (err) { console.error('Sign out error:', err); }
}

// ========== Voice — MediaRecorder (sends to /voice_chat) ==========
// Uses MediaRecorder so audio goes to the Flask backend for:
//   - Whisper STT transcription
//   - Wav2Vec2 SER emotion detection
//   - EARS reward model scoring

let mediaRecorder;
let audioChunks = [];
let isRecording = false;

voiceBtn.addEventListener("click", async () => {

    if (!isRecording) {
        // ── Start recording ──────────────────────────────────────────────
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder  = new MediaRecorder(stream);
            audioChunks    = [];
            isRecording    = true;

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) audioChunks.push(event.data);
            };

            mediaRecorder.start();
            voiceBtn.textContent = "⏹ Stop";
            voiceBtn.style.background = "linear-gradient(135deg, #E84855 0%, #c4303b 100%)";

        } catch (err) {
            console.error("Microphone access denied:", err);
            alert("Microphone access is required for voice input. Please allow microphone permissions.");
        }

    } else {
        // ── Stop recording ───────────────────────────────────────────────
        isRecording = false;
        voiceBtn.textContent = "🎤";
        voiceBtn.style.background = "";

        mediaRecorder.stop();

        // Stop all microphone tracks
        mediaRecorder.stream.getTracks().forEach(t => t.stop());

        mediaRecorder.onstop = async () => {

            const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
            const formData  = new FormData();
            formData.append("audio", audioBlob, "voice.webm");

            // Show typing indicator
            const typing = document.createElement('div');
            typing.className = 'msg bot';
            typing.innerHTML = `<div class='msg-content'><em>Processing voice...</em></div>`;
            messagesDiv.appendChild(typing);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;

            try {
                const res  = await fetch("/voice_chat", {
                    method: "POST",
                    body:   formData
                });
                const data = await res.json();
                typing.remove();

                if (res.ok) {
                    // Show transcribed text as user message
                    appendMessage("user", data.transcribed_text || "(voice message)");

                    // Show bot response with EARS feedback bar
                    const emotion = data.emotion || data.audio_emotion || "neutral";
                    lastUserQuery   = data.transcribed_text || "";
                    lastUserEmotion = emotion;
                    appendMessage("bot", data.response, data.message_id, data.transcribed_text, emotion);

                } else {
                    appendMessage("bot", "❌ Voice processing failed: " + (data.error || "Unknown error"));
                }
            } catch (err) {
                typing.remove();
                console.error("Voice chat error:", err);
                appendMessage("bot", "❌ Error connecting to server for voice processing.");
            }
        };
    }
});

// ========== Chat ==========
async function loadChatHistory() {
    try {
        const res  = await fetch('/history');
        const data = await res.json();
        if (data.history && data.history.length > 0) {
            messagesDiv.innerHTML = '';
            data.history.forEach(msg => appendMessage(msg.role, msg.message));
        }
    } catch (err) { console.error('Failed to load history:', err); }
}

function appendMessage(role, text, messageId = null, query = null, emotion = "neutral") {
    const emptyState = messagesDiv.querySelector('.empty-state');
    if (emptyState) emptyState.remove();

    const msgDiv = document.createElement('div');
    msgDiv.className = `msg ${role}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'msg-content';
    contentDiv.innerHTML = `<strong>${role === 'user' ? 'You' : 'Bot'}:</strong> ${escapeHtml(text)}`;
    msgDiv.appendChild(contentDiv);

    // EARS feedback bar for bot messages with a messageId
    if (role === 'bot' && messageId) {
        const feedbackQuery   = query   || lastUserQuery;
        const feedbackEmotion = emotion || lastUserEmotion;
        renderFeedback(messageId, feedbackQuery, text, msgDiv, feedbackEmotion);
    }

    messagesDiv.appendChild(msgDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

async function sendMessage() {
    const query = queryInput.value.trim();
    if (!query) return;

    lastUserQuery = query;
    appendMessage('user', query);
    queryInput.value = '';

    const typing = document.createElement('div');
    typing.className = 'msg bot';
    typing.innerHTML = `<div class='msg-content'><em>Typing...</em></div>`;
    messagesDiv.appendChild(typing);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    try {
        const res  = await fetch('/chat', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ query })
        });
        const data = await res.json();
        typing.remove();

        if (res.ok) {
            const emotion = data.emotion || 'neutral';
            lastUserEmotion = emotion;
            appendMessage('bot', data.response, data.message_id, query, emotion);
        } else {
            appendMessage('bot', `❌ Error: ${data.error || 'Unknown error'}`);
        }
    } catch (err) {
        typing.remove();
        appendMessage('bot', '❌ Error connecting to server.');
    }
}

// Enter key
queryInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

// File upload
fileInput.addEventListener('change', (e) => {
    const fileName = e.target.files[0]?.name || 'Choose a file to upload...';
    document.getElementById('fileName').textContent = fileName;
});

uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const file = fileInput.files[0];
    if (!file) { alert('Please select a file first'); return; }

    const formData = new FormData();
    formData.append('file', file);
    const fileName = document.getElementById('fileName');
    fileName.textContent = 'Uploading...';

    try {
        const res  = await fetch('/upload', { method: 'POST', body: formData });
        const data = await res.json();
        if (res.ok) {
            fileName.textContent = 'Upload successful! ✓';
            appendMessage('bot', `📄 ${data.message}`);
            setTimeout(() => { fileName.textContent = 'Choose a file to upload...'; fileInput.value = ''; }, 2000);
        } else {
            fileName.textContent = 'Upload failed ✗';
            appendMessage('bot', `❌ Upload error: ${data.error}`);
        }
    } catch (err) {
        fileName.textContent = 'Upload failed ✗';
        appendMessage('bot', '❌ Upload failed: Connection error');
    }
});

// ========== Initialize ==========
checkAuth();