/**
 * E.V. Agent Web UI — Frontend JavaScript v2.0
 * Modern Cyberpunk Interface, Audio Visualizer, Marked rendering, SFX engine.
 */

// ===== State Management =====
let isRecording = false;
let isProcessing = false;
let autoTTSEnabled = true;
let sfxEnabled = true;
let isSpeaking = false;
let recognition = null;
let currentAudioObject = null;
let currentTTSBtn = null;
let pendingAttachments = [];
let availableTools = [];
let selectedSuggestIndex = 0;
let visualizerState = 'IDLE'; // IDLE, LISTENING, THINKING, SPEAKING
let visualizerAnimFrame = null;
let sfxAudioCtx = null;

// ===== DOM Elements =====
const chatArea = document.getElementById('chatArea');
const chatWelcome = document.getElementById('chatWelcome');
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const micBtn = document.getElementById('micBtn');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const sidebar = document.getElementById('sidebar');

// ===== Initialization =====
document.addEventListener('DOMContentLoaded', () => {
    // Restore Saved Settings
    const savedTTS = localStorage.getItem('ev_auto_tts_enabled');
    if (savedTTS !== null) autoTTSEnabled = savedTTS === 'true';
    updateTTSToggleUI();

    const savedSFX = localStorage.getItem('ev_sfx_enabled');
    if (savedSFX !== null) sfxEnabled = savedSFX === 'true';
    updateSFXToggleUI();

    const savedSidebar = localStorage.getItem('ev_sidebar_state');
    if (savedSidebar === 'collapsed' && sidebar) {
        sidebar.classList.add('collapsed');
    }

    // Configure Marked & Highlight.js
    initMarkedRenderer();

    // Core Services
    checkStatus();
    loadTools();
    loadChatHistory();
    initSpeechRecognition();
    initSlashAutocomplete();
    initFileUpload();
    initTextareaAutoResize();
    initAudioVisualizer();
});

// ===== Configure Marked Markdown Renderer =====
function initMarkedRenderer() {
    if (typeof marked === 'undefined') return;

    const customRenderer = {
        code(codeArg, langArg) {
            let codeText = '';
            let language = 'text';

            if (typeof codeArg === 'object' && codeArg !== null) {
                codeText = codeArg.text || '';
                language = codeArg.lang || langArg || 'text';
            } else {
                codeText = codeArg || '';
                language = langArg || 'text';
            }

            language = (language || 'text').trim().toLowerCase();

            let highlighted = escapeHtml(codeText);
            if (typeof hljs !== 'undefined' && language && hljs.getLanguage(language)) {
                try {
                    highlighted = hljs.highlight(codeText, { language }).value;
                } catch (e) {
                    highlighted = escapeHtml(codeText);
                }
            }

            const encodedCode = encodeURIComponent(codeText);
            return `
                <div class="code-block-container">
                    <div class="code-header">
                        <span class="code-lang">${escapeHtml(language)}</span>
                        <button class="copy-code-btn" onclick="copyCodeFromAttr(this, '${encodedCode}')">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                            <span>Copy</span>
                        </button>
                    </div>
                    <pre><code class="hljs ${escapeHtml(language)}">${highlighted}</code></pre>
                </div>
            `;
        }
    };

    try {
        if (typeof marked.use === 'function') {
            marked.use({
                gfm: true,
                breaks: true,
                renderer: customRenderer
            });
        } else if (typeof marked.setOptions === 'function') {
            const renderer = new marked.Renderer();
            renderer.code = customRenderer.code;
            marked.setOptions({ renderer: renderer, gfm: true, breaks: true });
        }
    } catch (err) {
        console.warn('Marked init warning:', err);
    }
}

function renderMarkdown(text) {
    if (!text) return '';
    if (typeof marked !== 'undefined') {
        try {
            const result = marked.parse(text);
            if (typeof result === 'string') {
                return result;
            }
        } catch (e) {
            console.error('Marked parse error:', e);
        }
    }
    return escapeHtml(text).replace(/\n/g, '<br>');
}

// ===== Copy Code & Message Helpers =====
function copyCodeFromAttr(btn, encodedCode) {
    try {
        const codeText = decodeURIComponent(encodedCode);
        navigator.clipboard.writeText(codeText).then(() => {
            btn.classList.add('copied');
            btn.querySelector('span').textContent = 'Copied!';
            playSFX('click');
            setTimeout(() => {
                btn.classList.remove('copied');
                btn.querySelector('span').textContent = 'Copy';
            }, 2000);
        });
    } catch (e) {
        console.error('Copy failed:', e);
    }
}

function copyMessageContent(btn, msgId) {
    const msgContainer = document.getElementById(msgId);
    if (!msgContainer) return;
    const text = msgContainer.innerText;
    navigator.clipboard.writeText(text).then(() => {
        const label = btn.querySelector('.action-label');
        if (label) label.textContent = 'Copied!';
        playSFX('click');
        setTimeout(() => {
            if (label) label.textContent = 'Copy';
        }, 2000);
    });
}

// ===== Sidebar Management =====
function toggleSidebar() {
    if (!sidebar) return;
    sidebar.classList.toggle('collapsed');
    sidebar.classList.toggle('open');
    const isCollapsed = sidebar.classList.contains('collapsed');
    localStorage.setItem('ev_sidebar_state', isCollapsed ? 'collapsed' : 'expanded');
    playSFX('click');
}

function clearChatSession() {
    if (chatMessages) chatMessages.innerHTML = '';
    if (chatWelcome) chatWelcome.classList.remove('hidden');
    playSFX('click');
}

// ===== Textarea Auto Resize & Key Handler =====
function initTextareaAutoResize() {
    if (!messageInput) return;
    messageInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 160) + 'px';
    });

    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
            const popup = document.getElementById('slashSuggestPopup');
            if (popup && !popup.classList.contains('hidden')) {
                const list = document.getElementById('slashSuggestList');
                const items = list ? list.querySelectorAll('.slash-suggest-item') : [];
                if (items.length > 0) return;
            }
            e.preventDefault();
            sendMessage();
        }
    });
}

// ===== Web Audio SFX Engine =====
function playSFX(type) {
    if (!sfxEnabled) return;
    try {
        if (!sfxAudioCtx) {
            sfxAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (sfxAudioCtx.state === 'suspended') {
            sfxAudioCtx.resume();
        }
        const osc = sfxAudioCtx.createOscillator();
        const gain = sfxAudioCtx.createGain();
        osc.connect(gain);
        gain.connect(sfxAudioCtx.destination);

        const now = sfxAudioCtx.currentTime;
        if (type === 'send') {
            osc.type = 'sine';
            osc.frequency.setValueAtTime(440, now);
            osc.frequency.exponentialRampToValueAtTime(880, now + 0.1);
            gain.gain.setValueAtTime(0.12, now);
            gain.gain.exponentialRampToValueAtTime(0.01, now + 0.1);
            osc.start(now);
            osc.stop(now + 0.1);
        } else if (type === 'receive') {
            osc.type = 'triangle';
            osc.frequency.setValueAtTime(523.25, now);
            osc.frequency.exponentialRampToValueAtTime(659.25, now + 0.15);
            gain.gain.setValueAtTime(0.1, now);
            gain.gain.exponentialRampToValueAtTime(0.01, now + 0.15);
            osc.start(now);
            osc.stop(now + 0.15);
        } else if (type === 'click') {
            osc.type = 'sine';
            osc.frequency.setValueAtTime(800, now);
            gain.gain.setValueAtTime(0.05, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);
            osc.start(now);
            osc.stop(now + 0.04);
        } else if (type === 'mic') {
            osc.type = 'sine';
            osc.frequency.setValueAtTime(300, now);
            osc.frequency.exponentialRampToValueAtTime(600, now + 0.2);
            gain.gain.setValueAtTime(0.15, now);
            gain.gain.exponentialRampToValueAtTime(0.01, now + 0.2);
            osc.start(now);
            osc.stop(now + 0.2);
        }
    } catch (e) {
        // AudioContext disabled or blocked by policy
    }
}

function toggleSFX() {
    sfxEnabled = !sfxEnabled;
    localStorage.setItem('ev_sfx_enabled', sfxEnabled);
    updateSFXToggleUI();
    if (sfxEnabled) playSFX('click');
}

function updateSFXToggleUI() {
    const btn = document.getElementById('sfxToggleBtn');
    const icon = document.getElementById('sfxIcon');
    if (!btn || !icon) return;
    if (sfxEnabled) {
        btn.classList.add('active');
        icon.textContent = '🔊';
    } else {
        btn.classList.remove('active');
        icon.textContent = '🔇';
    }
}

// ===== Hologram Audio Visualizer =====
function initAudioVisualizer() {
    const canvas = document.getElementById('audioVisualizer');
    const label = document.getElementById('visualizerState');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let phase = 0;

    function render() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        phase += 0.08;

        const w = canvas.width;
        const h = canvas.height;
        const cy = h / 2;

        let strokeStyle = '#06b6d4';
        let amplitude = 4;
        let speedMult = 1;

        if (visualizerState === 'LISTENING') {
            strokeStyle = '#06b6d4';
            amplitude = 10;
            speedMult = 2;
            if (label) label.textContent = 'MIC LISTENING';
        } else if (visualizerState === 'THINKING') {
            strokeStyle = '#8b5cf6';
            amplitude = 8;
            speedMult = 1.5;
            if (label) label.textContent = 'THINKING';
        } else if (visualizerState === 'SPEAKING') {
            strokeStyle = '#f59e0b';
            amplitude = 12;
            speedMult = 2.2;
            if (label) label.textContent = 'E.V. SPEAKING';
        } else {
            strokeStyle = 'rgba(6, 182, 212, 0.5)';
            amplitude = 3;
            speedMult = 0.8;
            if (label) label.textContent = 'IDLE MATRIX';
        }

        ctx.beginPath();
        ctx.lineWidth = 2;
        ctx.strokeStyle = strokeStyle;

        for (let x = 0; x < w; x++) {
            const y = cy + Math.sin((x * 0.05) + (phase * speedMult)) * amplitude * Math.sin(x / w * Math.PI);
            if (x === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();

        visualizerAnimFrame = requestAnimationFrame(render);
    }
    render();
}

function setVisualizerState(state) {
    visualizerState = state;
}

// ===== Status & Backend Sync =====
function setStatus(state, text) {
    if (!statusDot || !statusText) return;
    statusDot.className = 'status-dot ' + state;
    statusText.textContent = text;

    if (state === 'online') setVisualizerState('IDLE');
    else if (state === 'listening') setVisualizerState('LISTENING');
    else if (state === 'thinking') setVisualizerState('THINKING');
    else if (state === 'speaking') setVisualizerState('SPEAKING');
}

async function checkStatus() {
    try {
        const res = await fetch('/api/status');
        if (res.ok) {
            const data = await res.json();
            if (data.status === 'online') {
                setStatus('online', 'Online');
                if (data.memory && data.memory.long_term_count !== undefined) {
                    const el = document.getElementById('chromaCount');
                    if (el) el.textContent = data.memory.long_term_count + ' items';
                }
            } else if (data.status === 'initializing') {
                setStatus('thinking', 'Initializing...');
                setTimeout(checkStatus, 3000);
            }
        } else {
            setStatus('offline', 'Offline');
            setTimeout(checkStatus, 5000);
        }
    } catch (err) {
        setStatus('offline', 'Offline');
        setTimeout(checkStatus, 5000);
    }
}



async function loadTools() {
    try {
        const res = await fetch('/api/tools');
        if (res.ok) {
            const data = await res.json();
            availableTools = data.tools || [];
            renderSidebarTools(availableTools);
        }
    } catch (e) {
        console.warn('Failed to load tools:', e);
    }
}

function renderSidebarTools(tools) {
    const grid = document.getElementById('toolsGrid');
    if (!grid || !tools.length) return;
    grid.innerHTML = tools.slice(0, 8).map(t => `<span class="tool-tag">${escapeHtml(t.name)}</span>`).join('');
}

// ===== Slash Autocomplete =====
function initSlashAutocomplete() {
    const popup = document.getElementById('slashSuggestPopup');
    const list = document.getElementById('slashSuggestList');
    if (!messageInput || !popup || !list) return;

    messageInput.addEventListener('input', () => {
        const val = messageInput.value;
        if (val.startsWith('/')) {
            const query = val.substring(1).toLowerCase().trim();
            const matches = availableTools.filter(t => 
                t.name.toLowerCase().includes(query) || 
                (t.description && t.description.toLowerCase().includes(query))
            );
            if (matches.length > 0) {
                renderSlashSuggestions(matches);
                showSlashPopup();
            } else {
                hideSlashPopup();
            }
        } else {
            hideSlashPopup();
        }
    });

    messageInput.addEventListener('keydown', (e) => {
        if (!popup || popup.classList.contains('hidden')) return;

        const items = list.querySelectorAll('.slash-suggest-item');
        if (items.length === 0) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            selectedSuggestIndex = (selectedSuggestIndex + 1) % items.length;
            updateSlashSelection(items);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            selectedSuggestIndex = (selectedSuggestIndex - 1 + items.length) % items.length;
            updateSlashSelection(items);
        } else if (e.key === 'Enter' || e.key === 'Tab') {
            if (selectedSuggestIndex >= 0 && selectedSuggestIndex < items.length) {
                e.preventDefault();
                items[selectedSuggestIndex].click();
            }
        } else if (e.key === 'Escape') {
            hideSlashPopup();
        }
    });
}

function showSlashPopup() {
    const popup = document.getElementById('slashSuggestPopup');
    if (popup) popup.classList.remove('hidden');
}

function hideSlashPopup() {
    const popup = document.getElementById('slashSuggestPopup');
    if (popup) popup.classList.add('hidden');
    selectedSuggestIndex = 0;
}

function renderSlashSuggestions(tools) {
    const list = document.getElementById('slashSuggestList');
    if (!list) return;
    list.innerHTML = '';
    selectedSuggestIndex = 0;

    tools.forEach((t, idx) => {
        const item = document.createElement('div');
        item.className = 'slash-suggest-item' + (idx === 0 ? ' selected' : '');
        item.dataset.index = idx;
        item.innerHTML = `
            <div class="slash-name">/${escapeHtml(t.name)}</div>
            <div class="slash-desc">${escapeHtml(t.description || '')}</div>
        `;
        item.onclick = () => {
            messageInput.value = `/${t.name} `;
            messageInput.focus();
            hideSlashPopup();
        };
        list.appendChild(item);
    });
}

function updateSlashSelection(items) {
    items.forEach((item, idx) => {
        if (idx === selectedSuggestIndex) {
            item.classList.add('selected');
            item.scrollIntoView({ block: 'nearest' });
        } else {
            item.classList.remove('selected');
        }
    });
}

// ===== File Uploads & Drag-Drop =====
function triggerFileInput() {
    const input = document.getElementById('fileInput');
    if (input) input.click();
}

function initFileUpload() {
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                handleFilesSelected(Array.from(e.target.files));
                fileInput.value = '';
            }
        });
    }

    // Drag & Drop
    const overlay = document.getElementById('dragDropOverlay');
    let dragCounter = 0;

    window.addEventListener('dragenter', (e) => {
        e.preventDefault();
        dragCounter++;
        if (overlay) overlay.classList.remove('hidden');
    });

    window.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dragCounter--;
        if (dragCounter <= 0) {
            dragCounter = 0;
            if (overlay) overlay.classList.add('hidden');
        }
    });

    window.addEventListener('dragover', (e) => e.preventDefault());

    window.addEventListener('drop', (e) => {
        e.preventDefault();
        dragCounter = 0;
        if (overlay) overlay.classList.add('hidden');
        if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFilesSelected(Array.from(e.dataTransfer.files));
        }
    });

    // Paste Image Ctrl+V
    window.addEventListener('paste', (e) => {
        if (e.clipboardData && e.clipboardData.files && e.clipboardData.files.length > 0) {
            const files = Array.from(e.clipboardData.files);
            const imageFiles = files.filter(f => f.type.startsWith('image/'));
            if (imageFiles.length > 0) {
                e.preventDefault();
                handleFilesSelected(imageFiles);
            }
        }
    });
}

async function handleFilesSelected(files) {
    for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        try {
            const res = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            if (res.ok) {
                const data = await res.json();
                pendingAttachments.push(data);
                renderAttachmentPreviews();
                playSFX('click');
            }
        } catch (err) {
            console.error('Upload error:', err);
        }
    }
}

function renderAttachmentPreviews() {
    const bar = document.getElementById('attachmentPreviewBar');
    if (!bar) return;
    if (pendingAttachments.length === 0) {
        bar.classList.add('hidden');
        bar.innerHTML = '';
        return;
    }
    bar.classList.remove('hidden');
    bar.innerHTML = pendingAttachments.map((att, idx) => `
        <div class="attachment-chip">
            ${att.is_image ? `<img src="${att.url}" class="chip-thumb">` : `<span class="chip-icon">📄</span>`}
            <span class="chip-name">${escapeHtml(att.filename)}</span>
            <span class="chip-remove" onclick="removeAttachment(${idx})">✕</span>
        </div>
    `).join('');
}

function removeAttachment(idx) {
    pendingAttachments.splice(idx, 1);
    renderAttachmentPreviews();
    playSFX('click');
}

// ===== Chat Messaging Logic =====
function sendQuickMessage(text) {
    if (!messageInput) return;
    messageInput.value = text;
    messageInput.style.height = 'auto';
    sendMessage();
}

async function sendMessage() {
    if (isProcessing) return;

    const rawMessage = messageInput.value.trim();
    if (!rawMessage && pendingAttachments.length === 0) return;

    // Reset Input
    messageInput.value = '';
    messageInput.style.height = 'auto';
    hideSlashPopup();

    // Hide Welcome Card
    if (chatWelcome) chatWelcome.classList.add('hidden');

    const attachmentsToSend = [...pendingAttachments];
    pendingAttachments = [];
    renderAttachmentPreviews();

    // Render User Message
    const msgId = 'user-' + Date.now();
    renderUserMessage(rawMessage, attachmentsToSend, msgId);
    playSFX('send');

    // UI Status Processing
    isProcessing = true;
    setStatus('thinking', 'Processing...');
    sendBtn.disabled = true;

    // Send Stream request
    await sendStreamMessage(rawMessage, attachmentsToSend);
}

function renderUserMessage(text, attachments, msgId) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message user';
    msgDiv.id = msgId;

    let attachHTML = '';
    if (attachments && attachments.length > 0) {
        attachHTML = `<div class="msg-attachments">` + attachments.map(att => {
            if (att.is_image) return `<img src="${att.url}" class="msg-attachment-img" onclick="window.open('${att.url}')">`;
            return `<a href="${att.url}" target="_blank" class="msg-attachment-doc">📄 ${escapeHtml(att.filename)}</a>`;
        }).join('') + `</div>`;
    }

    msgDiv.innerHTML = `
        <div class="message-avatar">👤</div>
        <div class="message-content-wrapper">
            <div class="message-content">
                ${attachHTML}
                ${escapeHtml(text)}
            </div>
        </div>
    `;
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
}

// ===== Stream Response Engine =====
async function sendStreamMessage(message, attachments) {
    const evMsgId = 'ev-' + Date.now();
    const evDiv = document.createElement('div');
    evDiv.className = 'message ev';
    evDiv.id = evMsgId;

    evDiv.innerHTML = `
        <div class="message-avatar">🕷️</div>
        <div class="message-content-wrapper" style="flex:1;">
            <div class="thinking-block hidden" id="thinking-${evMsgId}">
                <div class="thinking-header" onclick="toggleThinkingBlock('thinking-${evMsgId}')">
                    <div class="thinking-header-left">
                        <span class="thinking-icon">🧠</span>
                        <span class="thinking-title">Trình tự tư duy (Reasoning)</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span class="thinking-timer" id="timer-${evMsgId}">0.0s</span>
                        <span class="thinking-chevron">▼</span>
                    </div>
                </div>
                <div class="thinking-body" id="thinking-body-${evMsgId}"></div>
            </div>
            <div class="message-content" id="content-${evMsgId}">
                <span class="typing-cursor">▌</span>
            </div>
            <div class="msg-footer hidden" id="footer-${evMsgId}">
                <button class="msg-action-btn" onclick="copyMessageContent(this, 'content-${evMsgId}')">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                    <span class="action-label">Copy</span>
                </button>
                <button class="msg-action-btn msg-tts-btn" onclick="speakMessageText('content-${evMsgId}', this)">
                    <span>🔊</span> <span class="action-label">Đọc</span>
                </button>
            </div>
        </div>
    `;
    chatMessages.appendChild(evDiv);
    scrollToBottom();

    const thinkingBlock = document.getElementById(`thinking-${evMsgId}`);
    const thinkingBody = document.getElementById(`thinking-body-${evMsgId}`);
    const timerEl = document.getElementById(`timer-${evMsgId}`);
    const contentEl = document.getElementById(`content-${evMsgId}`);
    const footerEl = document.getElementById(`footer-${evMsgId}`);

    let startTime = Date.now();
    let timerInterval = setInterval(() => {
        if (timerEl) {
            timerEl.textContent = ((Date.now() - startTime) / 1000).toFixed(1) + 's';
        }
    }, 100);

    let fullContent = '';

    try {
        const response = await fetch('/api/chat/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, attachments, session_id: currentActiveSessionId })
        });

        if (!response.ok) throw new Error('Network error');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (let line of lines) {
                line = line.trim();
                if (line.startsWith('data:')) {
                    const jsonStr = line.substring(5).trim();
                    if (!jsonStr) continue;
                    try {
                        const data = JSON.parse(jsonStr);

                        if (data.type === 'thinking_start') {
                            if (thinkingBlock) thinkingBlock.classList.remove('hidden');
                        } else if (data.type === 'thinking_step') {
                            if (thinkingBlock) thinkingBlock.classList.remove('hidden');
                            if (thinkingBody) {
                                const stepDiv = document.createElement('div');
                                stepDiv.className = 'thinking-step';
                                stepDiv.textContent = data.step;
                                thinkingBody.appendChild(stepDiv);
                            }
                        } else if (data.type === 'tool_call') {
                            if (thinkingBlock) thinkingBlock.classList.remove('hidden');
                            if (thinkingBody) {
                                const stepDiv = document.createElement('div');
                                stepDiv.className = 'thinking-step tool-step';
                                stepDiv.innerHTML = `
                                    <div class="step-text">⚡ Gọi công cụ: <strong>${escapeHtml(data.name)}</strong></div>
                                    ${data.args ? `<div class="step-args">${escapeHtml(data.args)}</div>` : ''}
                                `;
                                thinkingBody.appendChild(stepDiv);
                                playSFX('click');
                            }
                        } else if (data.type === 'chunk') {
                            fullContent += data.content;
                            contentEl.innerHTML = renderMarkdown(fullContent) + '<span class="typing-cursor">▌</span>';
                            scrollToBottom();
                        } else if (data.type === 'thinking_done') {
                            clearInterval(timerInterval);
                        } else if (data.type === 'error') {
                            clearInterval(timerInterval);
                            fullContent += `\n\n⚠️ **Lỗi:** ${data.error}`;
                            contentEl.innerHTML = renderMarkdown(fullContent);
                        } else if (data.type === 'done') {
                            clearInterval(timerInterval);
                            contentEl.innerHTML = renderMarkdown(fullContent);
                            if (footerEl) footerEl.classList.remove('hidden');
                            playSFX('receive');

                            if (autoTTSEnabled && fullContent) {
                                speakText(fullContent, footerEl.querySelector('.msg-tts-btn'));
                            }
                        }
                    } catch (e) {
                        console.warn('JSON parse error:', e, jsonStr);
                    }
                }
            }
        }
    } catch (err) {
        clearInterval(timerInterval);
        contentEl.innerHTML = `<span style="color:var(--danger)">⚠️ Đã xảy ra lỗi khi kết nối với E.V. Agent: ${escapeHtml(err.message)}</span>`;
    } finally {
        isProcessing = false;
        sendBtn.disabled = false;
        setStatus('online', 'Online');
        loadChatHistory();
        scrollToBottom();
    }
}

function toggleThinkingBlock(blockId) {
    const block = document.getElementById(blockId);
    if (block) block.classList.toggle('collapsed');
}

// ===== Web Speech Recognition (Mic) =====
function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        if (micBtn) micBtn.title = 'Trình duyệt không hỗ trợ Web Speech API';
        return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'vi-VN';

    recognition.onstart = () => {
        isRecording = true;
        micBtn.classList.add('recording');
        setStatus('listening', 'Listening...');
        playSFX('mic');
    };

    recognition.onresult = (e) => {
        let transcript = '';
        for (let i = e.resultIndex; i < e.results.length; i++) {
            transcript += e.results[i][0].transcript;
        }
        if (messageInput) {
            messageInput.value = transcript;
            messageInput.style.height = 'auto';
            messageInput.style.height = Math.min(messageInput.scrollHeight, 160) + 'px';
        }
    };

    recognition.onend = () => {
        isRecording = false;
        micBtn.classList.remove('recording');
        setStatus('online', 'Online');
        if (messageInput && messageInput.value.trim()) {
            sendMessage();
        }
    };

    recognition.onerror = (e) => {
        console.error('Speech recognition error:', e);
        isRecording = false;
        micBtn.classList.remove('recording');
        setStatus('online', 'Online');
    };
}

function toggleMic() {
    if (!recognition) return;
    if (isRecording) {
        recognition.stop();
    } else {
        recognition.start();
    }
}

// ===== TTS Playback =====
function toggleAutoTTS() {
    autoTTSEnabled = !autoTTSEnabled;
    localStorage.setItem('ev_auto_tts_enabled', autoTTSEnabled);
    updateTTSToggleUI();
    playSFX('click');
}

function updateTTSToggleUI() {
    const btn = document.getElementById('ttsToggleBtn');
    const label = document.getElementById('ttsLabel');
    if (!btn) return;
    if (autoTTSEnabled) {
        btn.classList.add('active');
        if (label) label.textContent = 'Tự đọc';
    } else {
        btn.classList.remove('active');
        if (label) label.textContent = 'Tắt đọc';
    }
}

function speakMessageText(contentElemId, btn) {
    const el = document.getElementById(contentElemId);
    if (!el) return;
    speakText(el.innerText, btn);
}

async function speakText(text, btn) {
    if (isSpeaking && currentAudioObject) {
        currentAudioObject.pause();
        isSpeaking = false;
        if (currentTTSBtn) currentTTSBtn.classList.remove('playing');
        setStatus('online', 'Online');
        return;
    }

    try {
        setStatus('speaking', 'Speaking...');
        if (btn) {
            btn.classList.add('playing');
            currentTTSBtn = btn;
        }

        const res = await fetch('/api/tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });

        if (!res.ok) throw new Error('TTS failed');

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const audio = document.getElementById('ttsPlayer') || new Audio();
        audio.src = url;

        currentAudioObject = audio;
        isSpeaking = true;

        audio.onended = () => {
            isSpeaking = false;
            if (btn) btn.classList.remove('playing');
            setStatus('online', 'Online');
        };

        audio.play();
    } catch (e) {
        console.error('TTS error:', e);
        if (btn) btn.classList.remove('playing');
        setStatus('online', 'Online');
    }
}

// ===== Utilities =====
function scrollToBottom() {
    if (chatArea) {
        chatArea.scrollTo({
            top: chatArea.scrollHeight,
            behavior: 'smooth'
        });
    }
}

function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// ===== Sidebar Toggle & History Management =====
let currentActiveSessionId = null;

function toggleSidebar() {
    const sb = document.getElementById('sidebar');
    if (!sb) return;
    
    if (window.innerWidth <= 768) {
        sb.classList.toggle('open');
    } else {
        sb.classList.toggle('collapsed');
        const isCollapsed = sb.classList.contains('collapsed');
        localStorage.setItem('ev_sidebar_state', isCollapsed ? 'collapsed' : 'expanded');
    }
}

async function loadChatHistory() {
    const listContainer = document.getElementById('historySessionList');
    if (!listContainer) return;

    try {
        const res = await fetch('/api/history');
        if (!res.ok) throw new Error('Failed to fetch history');
        const data = await res.json();
        
        if (data.current_session_id && !currentActiveSessionId) {
            currentActiveSessionId = data.current_session_id;
        }

        const sessions = data.sessions || [];
        if (sessions.length === 0) {
            listContainer.innerHTML = '<div class="history-empty">Chưa có lịch sử trò chuyện</div>';
            return;
        }

        listContainer.innerHTML = sessions.map(s => {
            const isActive = s.session_id === currentActiveSessionId;
            const safeTitle = escapeHtml(s.title || 'Cuộc trò chuyện mới');
            return `
                <div class="history-session-item ${isActive ? 'active' : ''}" onclick="switchSession('${s.session_id}')" title="${safeTitle}">
                    <div class="history-item-left">
                        <span class="history-item-icon">💬</span>
                        <div class="history-item-details">
                            <span class="history-item-title">${safeTitle}</span>
                        </div>
                    </div>
                    <button class="history-delete-btn" onclick="deleteSession('${s.session_id}', event)" title="Xóa cuộc trò chuyện">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
                    </button>
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error('Error loading history:', e);
        listContainer.innerHTML = '<div class="history-empty">Chưa thể tải lịch sử</div>';
    }
}

async function switchSession(sessionId) {
    if (!sessionId) return;
    currentActiveSessionId = sessionId;
    
    try {
        const res = await fetch(`/api/history/${sessionId}`);
        if (!res.ok) throw new Error('Failed to load session');
        const data = await res.json();
        
        if (chatWelcome) chatWelcome.classList.add('hidden');
        if (chatMessages) {
            chatMessages.innerHTML = '';
            const messages = data.messages || [];
            messages.forEach(m => {
                appendMessageToUI(m.role === 'user' ? 'user' : 'ev', m.content, m.tool_calls);
            });
        }
        loadChatHistory();
    } catch (e) {
        console.error('Error switching session:', e);
    }
}

function appendMessageToUI(role, content, toolCalls) {
    if (!chatMessages || !content) return;
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    
    if (role === 'user') {
        msgDiv.innerHTML = `
            <div class="message-avatar">👤</div>
            <div class="message-content-wrapper">
                <div class="message-content">${escapeHtml(content)}</div>
            </div>
        `;
    } else {
        const formatted = typeof renderMarkdown === 'function' ? renderMarkdown(content) : escapeHtml(content);
        msgDiv.innerHTML = `
            <div class="message-avatar">🕷️</div>
            <div class="message-content-wrapper" style="flex:1;">
                <div class="message-content">${formatted}</div>
            </div>
        `;
    }
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
}

async function deleteSession(sessionId, event) {
    if (event) event.stopPropagation();
    if (!confirm('Bạn có chắc chắn muốn xóa cuộc trò chuyện này khỏi lịch sử?')) return;

    try {
        const res = await fetch(`/api/history/${sessionId}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('Failed to delete session');
        
        if (currentActiveSessionId === sessionId) {
            clearChatSession();
        } else {
            loadChatHistory();
        }
    } catch (e) {
        console.error('Error deleting session:', e);
    }
}

function clearChatSession() {
    currentActiveSessionId = 'session_' + new Date().toISOString().replace(/[-:T.]/g, '').slice(0, 15);
    if (chatMessages) chatMessages.innerHTML = '';
    if (chatWelcome) chatWelcome.classList.remove('hidden');
    loadChatHistory();
}
