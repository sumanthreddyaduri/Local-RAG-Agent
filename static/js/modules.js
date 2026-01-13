// ============== FIXED & CONSOLIDATED FEATURES (v4 Final) ==============
// Extracted from index.html inline script

// Note: Global state variables (fileViewMode, selectedFiles, currentContextFile) 
// are defined in app.js.

// Initialize runtime values from injected configuration
if (window.APP_CONFIG) {
    if (typeof currentMode !== 'undefined') currentMode = window.APP_CONFIG.mode;
    if (typeof currentSessionId !== 'undefined') currentSessionId = window.APP_CONFIG.currentSessionId;
}

// Model Switching Function (for native select dropdown)
async function selectModel(modelName) {
    console.log('Switching model to:', modelName);
    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: modelName })
        });
        if (response.ok) {
            showToast(`Model switched to ${modelName}`, 'success');
            // Reload page to reinitialize with new model
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast('Failed to switch model', 'error');
        }
    } catch (e) {
        console.error('Model switch error:', e);
        showToast('Failed to switch model', 'error');
    }
}

// Voice Input using Web Speech API with Waveform Visualization
let isRecording = false;
let recognition = null;

function startVoice() {
    // Check for browser support
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        alert('Voice input not supported in this browser. Try Chrome.');
        return;
    }

    const micBtn = document.querySelector('.chat-input-container .icon-btn[onclick="startVoice()"]') || document.querySelector('button[onclick="startVoice()"]');
    const chatInput = document.getElementById('chat-input');
    const waveform = document.getElementById('voice-waveform');
    const currentVal = chatInput ? chatInput.value : '';

    if (isRecording) {
        // Stop recording
        if (recognition) {
            recognition.stop();
        }
        isRecording = false;

        // Reset UI
        if (waveform) waveform.classList.remove('active');
        if (micBtn) micBtn.style.background = 'none';

        console.log('Voice: Stopped recording manually');
        return;
    }

    // Start recording
    console.log('Voice: Starting recording...');
    isRecording = true;

    // Update UI
    if (waveform) waveform.classList.add('active');
    if (micBtn) micBtn.style.background = 'rgba(220, 53, 69, 0.3)';

    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = function () {
        console.log('Voice: Speech recognition started');
    };

    recognition.onresult = function (event) {
        console.log('Voice: onresult', event);

        // Rebuild the transcript from the current session history
        let sessionTranscript = '';
        for (let i = 0; i < event.results.length; ++i) {
            sessionTranscript += event.results[i][0].transcript;
        }

        // Update input with everything heard so far
        if (chatInput) {
            // Logic: Initial Value + Space + New Session Text
            const prefix = currentVal + (currentVal && !currentVal.endsWith(' ') ? ' ' : '');
            chatInput.value = prefix + sessionTranscript;
        }

        // Update waveform status with last visualized chunk
        if (waveform) {
            const lastResult = event.results[event.results.length - 1];
            const statusText = lastResult ? lastResult[0].transcript : 'Listening...';
            const statusSpan = waveform.querySelector('span');
            if (statusSpan) statusSpan.innerText = statusText.slice(-30);
        }
    };

    recognition.onerror = function (event) {
        console.error('Voice: Speech error:', event.error, event);

        // Stop on error to reset state
        isRecording = false;
        if (waveform) waveform.classList.remove('active');
        if (micBtn) micBtn.style.background = 'none';

        if (event.error === 'not-allowed') {
            alert('Microphone access denied. Please allow microphone.');
        }
    };

    recognition.onend = function () {
        console.log('Voice: Speech recognition ended');
        if (isRecording) {
            isRecording = false;
            if (waveform) waveform.classList.remove('active');
            if (micBtn) micBtn.style.background = 'none';
            if (chatInput) chatInput.focus();
        }
    };

    try {
        recognition.start();
        console.log('Recognition started successfully');
    } catch (e) {
        console.error('Recognition start error:', e);
        isRecording = false;
    }
}

// Initialize Choices.js for model dropdown
document.addEventListener('DOMContentLoaded', function () {
    const modelSelect = document.getElementById('model-select');
    if (modelSelect && typeof Choices !== 'undefined') {
        const modelChoices = new Choices(modelSelect, {
            searchEnabled: false,
            shouldSort: false,
            itemSelectText: '',
            classNames: {
                containerOuter: 'choices',
            }
        });

        // Add custom class safely after initialization
        modelChoices.containerOuter.element.classList.add('model-choices');

        // Handle change event
        modelSelect.addEventListener('change', function (e) {
            selectModel(e.detail.value);
        });
    }
});

// 1. Theme Toggle
// toggleTheme and updateThemeIcon removed - using main.js implementation

// 2. Loading States & Stats
// loadStats REMOVED - using main.js implementation (which has dashboard empty state logic)


// 3. File Management
// loadFiles and renderFiles are now handled by main.js
// Accessing global functions instead.

// Ensure no old functions leak
// window.renderFiles = renderFiles; // Removed


async function uploadFiles(files) {
    if (!files || files.length === 0) return;
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }
    showToast('Uploading files...', 'info');
    try {
        const response = await fetch('/api/files/upload', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        if (data.status === 'success') {
            showToast(`Uploaded ${data.uploaded.length} files`, 'success');
            loadFiles();
            loadStats();
        } else {
            showToast('Upload failed: ' + (data.message || 'Unknown error'), 'error');
        }
    } catch (e) {
        showToast('Upload error: ' + e.message, 'error');
    }
}

function handleDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    document.getElementById('drop-zone').classList.remove('drag-over');
    const files = event.dataTransfer.files;
    uploadFiles(files);
}

function handleFileSelect(event) {
    const files = event.target.files;
    uploadFiles(files);
    event.target.value = '';
}

// Selection functions - disabled/dummy
function toggleFileSelection(filename, event) {
    if (event) event.stopPropagation();
}

function deleteSelectedFiles() {
    // Disabled
}

function clearSelection() {
    // Disabled
}

// Fix: Single Delete
async function deleteFile(filename) {
    if (!confirm(`Delete "${filename}"?`)) return;

    showToast('Deleting...', 'info');
    try { // Ensure double encoded for path safety
        const response = await fetch(`/api/files/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });
        const data = await response.json();

        if (data.status === 'success') {
            loadFiles();
            loadStats();
            showToast('File deleted', 'success');
            // Ensure menu closes
            const menu = document.getElementById('context-menu');
            if (menu) {
                menu.classList.remove('visible');
                menu.style.display = 'none';
            }
        } else {
            showToast('Failed to delete: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (e) {
        showToast('Error deleting file: ' + e.message, 'error');
    }
}

// 4. File Preview
async function showPreview(filename) {
    currentContextFile = filename;
    const modal = document.getElementById('preview-modal');
    const content = document.getElementById('preview-content');
    const title = document.getElementById('preview-filename');

    title.textContent = filename;
    content.innerHTML = '<div class="loading">Loading preview...</div>';

    modal.classList.remove('hidden');
    modal.classList.add('show');

    try {
        const response = await fetch(`/api/files/preview/${encodeURIComponent(filename)}`);
        const data = await response.json();

        if (data.error) {
            content.innerHTML = `<div class="preview-error">❌ ${data.error}</div>`;
        } else if (data.type === 'text') {
            content.innerHTML = `<pre class="preview-text">${escapeHtml(data.content)}</pre>`;
        } else if (data.type === 'image') {
            content.innerHTML = `<div style="text-align:center"><img src="${data.url}" class="preview-image" style="max-width:100%; max-height:60vh;"></div>`;
        } else {
            content.innerHTML = `<div class="preview-info"><p>${data.content}</p></div>`;
        }
    } catch (e) {
        content.innerHTML = `<div class="preview-error">❌ Failed to load preview</div>`;
    }
}

function closePreviewModal() {
    const modal = document.getElementById('preview-modal');
    modal.classList.remove('show');
    modal.classList.add('hidden');
    currentContextFile = null;
}

async function ingestPreviewFile() {
    if (!currentContextFile) return;
    showToast(`Ingesting ${currentContextFile}...`, 'info');
    try {
        const response = await fetch(`/api/files/${encodeURIComponent(currentContextFile)}/ingest`, {
            method: 'POST'
        });
        const data = await response.json();
        if (data.status === 'success') {
            showToast('File ingested successfully', 'success');
            loadStats();
            closePreviewModal();
        } else {
            showToast('Ingest failed: ' + data.error, 'error');
        }
    } catch (e) {
        showToast('Ingest error: ' + e.message, 'error');
    }
}

async function deleteModel(name) {
    if (!confirm(`Delete model "${name}"? This cannot be undone.`)) return;

    try {
        const response = await fetch(`/api/models/${encodeURIComponent(name)}`, { method: 'DELETE' });
        const data = await response.json();

        if (data.status === 'success') {
            showToast('Model deleted', 'success');
            fetchModelsForControls();
        } else {
            showToast('Delete failed: ' + data.error, 'error');
        }
    } catch (e) {
        showToast('Error: ' + e.message, 'error');
    }
}

// 5. View Navigation
showView = function (viewId) {
    localStorage.setItem('lastView', viewId);
    document.querySelectorAll('.view-section').forEach(el => el.classList.add('hidden'));
    document.getElementById('input-bar').classList.add('hidden');

    // FIX: Toggle main-content padding for full-height views (Settings, Files, Controls)
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        const fullHeightViews = ['settings', 'files', 'controls'];
        if (fullHeightViews.includes(viewId)) {
            mainContent.classList.add('no-padding-bottom');
        } else {
            mainContent.classList.remove('no-padding-bottom');
        }
    }

    // Hide chat-empty-state when switching away from chat
    const chatEmptyState = document.getElementById('chat-empty-state');
    if (chatEmptyState && viewId !== 'chat') {
        chatEmptyState.style.display = 'none';
    }

    let targetId = viewId + '-view'; // fallback
    if (viewId === 'controls') targetId = 'control-panel';
    if (viewId === 'dashboard') targetId = 'dashboard-view';
    if (viewId === 'files') targetId = 'files-view';
    if (viewId === 'chat') targetId = 'chat-view';
    if (viewId === 'settings') targetId = 'settings-view';

    const target = document.getElementById(targetId);
    if (target) target.classList.remove('hidden');

    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
        const onclick = btn.getAttribute('onclick');
        if (onclick && onclick.includes(`'${viewId}'`)) {
            btn.classList.add('active');
        }
        // Also check ID
        if (btn.id === `nav-btn-${viewId}`) btn.classList.add('active');
    });

    if (viewId === 'files') loadFiles();
    if (viewId === 'dashboard') loadStats();
    // if (viewId === 'extensions') loadKnowledgeGraph(); // Feature removed
    if (viewId === 'chat') {
        document.getElementById('input-bar').classList.remove('hidden');
        scrollToBottom();
    }
};

// 6. Helpers
function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    const icons = {
        'pdf': '📕', 'doc': '📘', 'docx': '📘', 'txt': '📄', 'md': '📝',
        'json': '📋', 'csv': '📊', 'xls': '📗', 'xlsx': '📗',
        'png': '🖼️', 'jpg': '🖼️', 'jpeg': '🖼️', 'gif': '🖼️',
        'py': '🐍', 'js': '📜', 'html': '🌐', 'css': '🎨'
    };
    return icons[ext] || '📁';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function formatDate(timestamp) {
    return new Date(timestamp * 1000).toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric'
    });
}

// escapeHtml REMOVED - using main.js implementation

// showToast is handled by main.js

window.alert = function (msg) { showToast(msg, 'warning'); };

// Context Menu
function showContextMenu(event, type, id) {
    event.preventDefault();
    event.stopPropagation();
    const menu = document.getElementById('context-menu');

    // Escape single quotes for inline onclick handlers
    const safeId = id.replace(/'/g, "\\'");

    let items = '';
    if (type === 'indexed') {
        items = `
            <div class="context-menu-item" onclick="showPreview('${safeId}')">
                Preview
            </div>
            <div class="context-menu-item danger" onclick="deleteFile('${safeId}')">
                Remove
            </div>
        `;
    }
    menu.innerHTML = items;

    let x = event.clientX;
    let y = event.clientY;

    menu.style.display = 'block';
    menu.classList.add('visible');

    const rect = menu.getBoundingClientRect();
    if (x + rect.width > window.innerWidth) x = window.innerWidth - rect.width - 10;
    if (y + rect.height > window.innerHeight) y = window.innerHeight - rect.height - 10;

    menu.style.top = `${y}px`;
    menu.style.left = `${x}px`;
}

// Window click listener to close context menu
window.addEventListener('click', (e) => {
    const menu = document.getElementById('context-menu');
    if (menu && menu.classList.contains('visible')) {
        if (!menu.contains(e.target)) {
            menu.classList.remove('visible');
            menu.style.display = 'none';
        }
    }
});

// Session Context Menu and Export functions moved to main.js

// Initialize runtime values (variables declared in app.js)
// currentMode, currentSessionId are set in index.html script block usually, so we need to be careful.
// They are likely set BEFORE this script runs if we put this script at the end.

// Unified file staging (max 5 files)
let currentFiles = []; // {type: 'image'|'document', name: string, data: base64, addToRag: boolean}
const MAX_FILES = 5;
let pendingRagDocs = []; // Documents awaiting RAG confirmation


// NOTE: Initialization now handled by initApp() in main.js

// ============== MODEL MANAGEMENT ==============
function handleModelChange(value) {
    if (value === '__manage__') {
        // Navigate to Controls page and scroll to Model Management
        showView('control-panel');
        fetchModelsForControls();
        setTimeout(() => {
            document.getElementById('model-management-section')?.scrollIntoView({ behavior: 'smooth' });
        }, 100);
        // Reset dropdown to current model
        const select = document.getElementById('model-select');
        if (select) select.value = window.APP_CONFIG.model;
    } else {
        selectModel(value);
    }
}

async function fetchModelsForControls() {
    const tbody = document.getElementById('model-list-body');
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="4" style="padding: 15px; text-align: center;">Loading...</td></tr>';

    try {
        const response = await fetch('/api/models');
        const data = await response.json();

        tbody.innerHTML = data.models.map(m => `
            <tr>
                <td style="padding: 8px;"><strong>${m.name}</strong></td>
                <td>${m.size}</td>
                <td>${m.modified ? new Date(m.modified).toLocaleDateString() : '-'}</td>
                <td>
                    <button onclick="deleteModel('${m.name}')" class="icon-btn" title="Delete" style="color: #e74c3c;">🗑️</button>
                </td>
            </tr>
        `).join('');

        // Also update the dropdown
        updateModelDropdown(data.models.map(m => m.name));

    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="4" style="color: #e74c3c; padding: 15px;">Error: ${e.message}</td></tr>`;
    }
}

function updateModelDropdown(models) {
    const select = document.getElementById('model-select');
    if (!select) return;

    // We can't access {{ config.model }} here easily if it's dynamic.
    // We should rely on what's selected or passed in.
    const current = select.value;

    let html = models.map(m =>
        `<option value="${m}" ${m === current ? 'selected' : ''}>${m}</option>`
    ).join('');
    html += '<option value="__manage__">⚙️ Manage Models...</option>';
    select.innerHTML = html;
}

async function pullNewModel() {
    const input = document.getElementById('new-model-name');
    const modelName = input.value.trim();
    const logBox = document.getElementById('pull-logs');
    const btn = document.getElementById('pull-btn');

    if (!modelName) {
        showToast('Please enter a model name', 'error');
        return;
    }

    logBox.style.display = 'block';
    logBox.innerText = `Starting pull for ${modelName}...\n`;
    btn.disabled = true;
    input.disabled = true;

    try {
        const response = await fetch('/api/models/pull', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: modelName })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (!line.trim()) continue;
                try {
                    const data = JSON.parse(line);
                    logBox.innerText += data.message + '\n';
                    logBox.scrollTop = logBox.scrollHeight;

                    if (data.status === 'success') {
                        showToast(`Pulled ${modelName} successfully!`, 'success');
                        fetchModelsForControls();
                    }
                } catch (e) {
                    // Not JSON, just append raw line
                    logBox.innerText += line + '\n';
                }
            }
        }
    } catch (e) {
        logBox.innerText += `\nError: ${e.message}`;
        showToast('Pull failed: ' + e.message, 'error');
    } finally {
        btn.disabled = false;
        input.disabled = false;
        input.value = '';
    }
}

function toggleMode() {
    const btn = document.getElementById('btn-toggle');
    const status = document.getElementById('mode-status');

    if (currentMode === 'cli') {
        currentMode = 'browser';
        btn.innerText = '🖥️ CLI Mode';
        if (status) status.innerHTML = 'Mode: <strong>Browser Chat</strong>';
        showView('chat');
    } else {
        currentMode = 'cli';
        btn.innerText = '💬 Chat Mode';
        if (status) status.innerHTML = 'Mode: <strong>CLI Chat</strong>';
        showView('controls');
    }

    fetch('/set_mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: currentMode })
    }).catch(console.error);
}

// Modal functions
function showConfirmModal(message, onConfirm) {
    document.getElementById('confirm-modal-message').textContent = message;
    const modal = document.getElementById('confirm-modal');
    const okBtn = document.getElementById('confirm-modal-ok');

    // Replace OK button click handler
    okBtn.onclick = function () {
        hideConfirmModal();
        onConfirm();
    };

    modal.style.display = 'flex';
}

function hideConfirmModal() {
    document.getElementById('confirm-modal').style.display = 'none';
}

function deleteSession(id, event) {
    if (event) event.stopPropagation();

    const sessionId = parseInt(id);

    showConfirmModal('Delete this chat session? This cannot be undone.', async function () {
        console.log('Deleting session:', sessionId);

        try {
            const response = await fetch(`/api/sessions/${sessionId}`, { method: 'DELETE' });
            console.log('Delete response status:', response.status);

            if (response.ok) {
                if (parseInt(currentSessionId) === sessionId) {
                    currentSessionId = null;
                    document.getElementById('chat-history').innerHTML =
                        '<div class="empty-state"><p>Select or create a chat to begin</p></div>';
                }
                await loadSessions();
                loadStats();
                showToast('Session deleted', 'success');
            } else {
                const data = await response.json();
                showToast('Delete failed: ' + (data.error || response.status), 'error');
            }
        } catch (e) {
            console.error('Delete error:', e);
            showToast('Delete error: ' + e.message, 'error');
        }
    });
}

async function loadChatHistory() {
    if (!currentSessionId) return;
    const sessionId = parseInt(currentSessionId);
    console.log('Loading chat history for session:', sessionId);

    const historyContainer = document.getElementById('chat-history');
    historyContainer.innerHTML = '<div class="loading">Loading history...</div>';

    try {
        const url = `/api/sessions/${sessionId}`;
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (data.messages && data.messages.length > 0) {
            historyContainer.innerHTML = data.messages.map(msg => {
                let contentHtml = formatMessage(msg);

                // Parse Metadata for Attachments
                try {
                    const meta = typeof msg.metadata === 'string' ? JSON.parse(msg.metadata) : (msg.metadata || {});
                    if (meta.files && Array.isArray(meta.files) && meta.files.length > 0) {
                        let attachmentsHtml = '<div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 5px;">';
                        meta.files.forEach(f => {
                            if (f.type === 'image') {
                                attachmentsHtml += `<img src="${f.path}" style="max-width: 150px; max-height: 150px; border-radius: 8px; object-fit: cover; cursor: pointer; border: 1px solid var(--border-color);" onclick="window.open('${f.path}', '_blank')" title="${f.name}">`;
                            } else {
                                attachmentsHtml += `<a href="${f.path}" target="_blank" style="text-decoration: none;"><span style="background: rgba(79, 172, 254, 0.1); border: 1px solid var(--accent-color); border-radius: 12px; padding: 4px 10px; font-size: 0.85em; color: var(--text-color); display: inline-flex; align-items: center; gap: 4px;">📄 ${f.name}</span></a>`;
                            }
                        });
                        attachmentsHtml += '</div>';
                        contentHtml += attachmentsHtml;
                    }
                } catch (e) {
                    console.error('Error parsing message metadata:', e);
                }

                return `
                <div class="message ${msg.role}-message">
                    <div class="message-content">${contentHtml}</div>
                    <div class="message-meta">${new Date(msg.created_at).toLocaleTimeString()}</div>
                </div>
            `}).join('');
        } else {
            historyContainer.innerHTML = '<div class="empty-state"><p>Start a new conversation</p></div>';
        }
        setTimeout(scrollToBottom, 100);
    } catch (e) {
        console.error('loadChatHistory error:', e);
        historyContainer.innerHTML = '<div class="error-message">Failed to load history</div>';
    }
}

let isVoiceActive = false;
const synth = window.speechSynthesis;

function toggleVoice() {
    isVoiceActive = !isVoiceActive;
    const btn = document.getElementById('voice-toggle-btn');
    btn.innerHTML = isVoiceActive ? '🔊' : '🔇';
    btn.classList.toggle('active', isVoiceActive);

    if (!isVoiceActive) {
        synth.cancel();
    } else {
        showToast("Voice Mode Activated", "success");
    }
}

function speakText(text) {
    if (!isVoiceActive) return;
    // Cancel previous
    synth.cancel();

    // Strip markdown chars for cleaner speech
    const cleanText = text.replace(/[*#`]/g, '');

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    synth.speak(utterance);
}

function speakLastResponse() {
    if (!isVoiceActive) return;
    // Get all assistant messages
    const messages = document.querySelectorAll('.assistant-message .message-content');
    if (messages.length > 0) {
        const lastMsg = messages[messages.length - 1];
        if (lastMsg) speakText(lastMsg.innerText);
    }
}

function formatMessage(msg) {
    let content = msg.content || '';
    if (msg.role === 'assistant') {
        // 1. Markdown
        content = typeof marked !== 'undefined' ? marked.parse(content) : content;

        // 2. Citations: "Source: filename" -> badge
        content = content.replace(/(?:^|\n)Source:\s*([^\n<]+)/gi, (match, filename) => {
            const fname = filename.trim();
            return `<br><span class="source-badge" onclick="showPreview('${fname}')" title="Preview Source">📄 ${fname}</span>`;
        });
    }
    return content;
}

function scrollToBottom() {
    const chatView = document.getElementById('chat-view');
    const history = document.getElementById('chat-history');
    if (!chatView) return;

    // Ensure anchor exists
    let anchor = document.getElementById('chat-scroll-anchor');
    if (!anchor && history) {
        anchor = document.createElement('div');
        anchor.id = 'chat-scroll-anchor';
        anchor.style.cssText = 'height: 1px; width: 100%;';
        history.appendChild(anchor);
    }

    // Scroll Logic
    const doScroll = () => {
        if (anchor) {
            anchor.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }
        if (chatView.scrollHeight - chatView.scrollTop > 500) {
            chatView.scrollTop = chatView.scrollHeight;
        }
    };

    doScroll();
    requestAnimationFrame(doScroll);
    setTimeout(doScroll, 100);
    setTimeout(doScroll, 300);
    setTimeout(doScroll, 800);
}

// Add Scroll Listener for "Scroll to Bottom" Button
(function initScrollListener() {
    const chatView = document.getElementById('chat-view');

    if (chatView) {
        chatView.addEventListener('scroll', () => {
            const btn = document.getElementById('scroll-bottom-btn');
            if (!btn) return;

            const threshold = 150;
            const distanceToBottom = chatView.scrollHeight - chatView.scrollTop - chatView.clientHeight;

            if (distanceToBottom > threshold) {
                btn.classList.add('visible');
            } else {
                btn.classList.remove('visible');
            }
        });
    }
})();

// Initial Load
loadSessions();

// Show default view or last used view
(function initDefaultView() {
    const lastView = localStorage.getItem('lastView');
    showView(lastView || 'controls');

    if (lastView === 'chat') {
        setTimeout(scrollToBottom, 500);
    }
})();

// Sidebar Resize Functionality
(function initSidebarResize() {
    const sidebar = document.querySelector('.sidebar');
    const handle = document.getElementById('sidebar-resize-handle');
    if (!sidebar || !handle) return;

    const MIN_WIDTH = 180;
    const MAX_WIDTH = 400;
    let isResizing = false;

    const savedWidth = localStorage.getItem('sidebarWidth');
    if (savedWidth) {
        const width = parseInt(savedWidth);
        if (width >= MIN_WIDTH && width <= MAX_WIDTH) {
            sidebar.style.width = width + 'px';
        }
    }

    handle.addEventListener('mousedown', function (e) {
        isResizing = true;
        handle.classList.add('active');
        document.body.style.cursor = 'ew-resize';
        document.body.style.userSelect = 'none';
        e.preventDefault();
    });

    document.addEventListener('mousemove', function (e) {
        if (!isResizing) return;
        const newWidth = e.clientX;
        if (newWidth >= MIN_WIDTH && newWidth <= MAX_WIDTH) {
            sidebar.style.width = newWidth + 'px';
        }
    });

    document.addEventListener('mouseup', function () {
        if (isResizing) {
            isResizing = false;
            handle.classList.remove('active');
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
            localStorage.setItem('sidebarWidth', sidebar.offsetWidth);
        }
    });
})();

async function clearIndex() {
    if (!confirm('Are you sure you want to clear ALL indexed documents? This cannot be undone.')) {
        return;
    }

    showToast('Clearing index...', 'info');
    try {
        const response = await fetch('/api/index/clear', { method: 'POST' });
        const data = await response.json();

        if (data.status === 'success') {
            showToast('Index cleared successfully', 'success');
            loadStats();
            loadFiles();
        } else {
            showToast('Failed to clear index: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (e) {
        showToast('Error clearing index: ' + e.message, 'error');
    }
}

// RAG Confirmation Modal
function showRagPrompt(fileObj) {
    const modal = document.createElement('div');
    modal.id = 'rag-modal';
    modal.style.cssText = `
        position: fixed; top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center;
        z-index: 10000;
    `;
    modal.innerHTML = `
        <div style="background: var(--bg-secondary); border-radius: 12px; padding: 24px; max-width: 400px; text-align: center; border: 1px solid var(--border-color);">
            <div style="font-size: 40px; margin-bottom: 12px;">📄</div>
            <h3 style="margin: 0 0 8px 0; color: white;">Add to RAG?</h3>
            <p style="color: var(--text-muted); margin-bottom: 16px; font-size: 0.9em;">
                "${fileObj.name}"<br>
                <small>Yes = Index for future queries. No = Temp analysis only.</small>
            </p>
            <div style="display: flex; gap: 12px; justify-content: center;">
                <button onclick="confirmRag(true)" class="primary-btn" style="padding: 8px 24px;">Yes</button>
                <button onclick="confirmRag(false)" style="padding: 8px 24px; background: var(--bg-tertiary); color: white; border: 1px solid var(--border-color); border-radius: 6px; cursor: pointer;">No</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

function confirmRag(addToRag) {
    const modal = document.getElementById('rag-modal');
    if (modal) modal.remove();

    if (pendingRagDocs.length > 0) {
        const doc = pendingRagDocs.shift();
        doc.addToRag = addToRag;
        currentFiles.push(doc);
        renderFilePreviews();
        showToast(`Document "${doc.name}" attached${addToRag ? ' (will add to RAG)' : ' (temp only)'}`, 'success');

        if (pendingRagDocs.length > 0) {
            setTimeout(() => showRagPrompt(pendingRagDocs[0]), 300);
        }
    }
}

function renderFilePreviews() {
    const imgContainer = document.getElementById('image-previews');
    const docContainer = document.getElementById('doc-previews');
    if (!imgContainer || !docContainer) return;

    imgContainer.innerHTML = '';
    docContainer.innerHTML = '';

    const images = currentFiles.filter(f => f.type === 'image');
    const docs = currentFiles.filter(f => f.type === 'document');

    imgContainer.style.display = images.length > 0 ? 'flex' : 'none';
    docContainer.style.display = docs.length > 0 ? 'flex' : 'none';

    images.forEach((img, idx) => {
        const realIdx = currentFiles.indexOf(img);
        const thumb = document.createElement('div');
        thumb.className = 'preview-thumb';
        thumb.style.backgroundImage = `url(${img.data})`;

        const remove = document.createElement('div');
        remove.className = 'preview-remove';
        remove.innerHTML = '×';
        remove.onclick = () => removeFile(realIdx);

        thumb.appendChild(remove);
        imgContainer.appendChild(thumb);
    });

    docs.forEach((doc, idx) => {
        const realIdx = currentFiles.indexOf(doc);
        const chip = document.createElement('div');
        chip.className = 'doc-chip';
        chip.style.cssText = 'display: flex; align-items: center; gap: 6px; background: rgba(79, 172, 254, 0.2); border: 1px solid var(--accent-color); border-radius: 20px; padding: 4px 12px; font-size: 0.85em; color: white;';

        chip.innerHTML = `
            <span style="font-size: 14px;">${doc.addToRag ? '📄✓' : '📄'}</span>
            <span style="max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${doc.name}</span>
            <span onclick="removeFile(${realIdx})" style="cursor: pointer; color: #ff6b6b; font-weight: bold;">×</span>
        `;

        docContainer.appendChild(chip);
    });
}

function removeFile(index) {
    currentFiles.splice(index, 1);
    renderFilePreviews();
}

// loadSettings removed - integrated into main.js

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const mode = btn.dataset.mode;
            if (mode) setMode(mode);
        });
    });
    // loadSettings is called by main.js
});

// setMode REMOVED - using main.js implementation

function setFileView(mode) {
    fileViewMode = mode;
    loadFiles();
    document.querySelectorAll('.view-toggle button').forEach(btn => btn.classList.remove('active'));
    if (mode === 'grid') document.getElementById('grid-view-btn')?.classList.add('active');
    if (mode === 'list') document.getElementById('list-view-btn')?.classList.add('active');
}


