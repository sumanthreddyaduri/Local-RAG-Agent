/**
 * RAG Agent Control Room - Main Application JavaScript
 * Extracted from index.html for modularity
 * Version: 3.0 - Modernized UI
 */

// ============== CONFIGURE MARKED + HIGHLIGHT.JS ==============
if (typeof marked !== 'undefined') {
    marked.setOptions({
        highlight: function (code, lang) {
            if (typeof hljs !== 'undefined' && lang && hljs.getLanguage(lang)) {
                return hljs.highlight(code, { language: lang }).value;
            }
            return typeof hljs !== 'undefined' ? hljs.highlightAuto(code).value : code;
        },
        breaks: true,
        gfm: true
    });
}

// ============== GLOBAL STATE ==============
let fileViewMode = 'grid';
let selectedFiles = new Set();
let currentContextFile = null;
let currentMode = 'cli';
let currentSessionId = null;

// ============== STARTER QUERY (Chat Chips) ==============
function sendStarterQuery(query) {
    // Hide empty state
    const emptyState = document.getElementById('chat-empty-state');
    if (emptyState) emptyState.style.display = 'none';

    // Set the input and send
    const input = document.getElementById('chat-input');
    if (input) {
        input.value = query;
        sendMessage();
    }
}

// ============== THEME ==============
function toggleTheme() {
    document.body.classList.toggle('dark-theme');
    const isDark = document.body.classList.contains('dark-theme');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    updateThemeIcon(isDark);
}

function updateThemeIcon(isDark) {
    const icon = document.getElementById('theme-icon');
    if (icon) {
        // Moon for Dark, Sun for Light (showing CURRENT state)
        icon.src = isDark
            ? 'https://img.icons8.com/?id=26031&format=png&size=24'  // Moon
            : 'https://img.icons8.com/?id=648&format=png&size=24';   // Sun
    }
}

// ============== SETTINGS MANAGEMENT ==============
async function updateSetting(key, value) {
    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ [key]: value })
        });
        const data = await response.json();
        if (data.status === 'success') {
            console.log(`Setting ${key} updated`);
        } else {
            console.error('Failed to update setting:', data.error);
        }
    } catch (error) {
        console.error('Error updating setting:', error);
    }
}

async function saveAllSettings() {
    // Collect all settings from form inputs
    const settings = {
        embed_model: document.getElementById('embed-model')?.value,
        chunk_size: parseInt(document.getElementById('chunk-size')?.value) || 500,
        chunk_overlap: parseInt(document.getElementById('chunk-overlap')?.value) || 50,
        retrieval_k: parseInt(document.getElementById('retrieval-k')?.value) || 4,
        use_hybrid_search: document.getElementById('hybrid-search')?.checked || false,
        hybrid_alpha: parseFloat(document.getElementById('hybrid-alpha')?.value) || 0.5,
        max_history_context: parseInt(document.getElementById('max-history')?.value) || 10,
        show_sources: document.getElementById('show-sources')?.checked || false,
        enable_tts: document.getElementById('tts-toggle')?.checked || false
    };

    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        const data = await response.json();
        if (data.status === 'success') {
            alert('✅ All settings saved successfully!');
        } else {
            alert('❌ Failed to save settings: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        alert('❌ Error saving settings: ' + error.message);
    }
}

async function resetSettings() {
    if (!confirm('Are you sure you want to reset all settings to defaults? This cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch('/api/settings/reset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        if (data.status === 'success') {
            alert('✅ Settings reset to defaults. Reloading page...');
            window.location.reload();
        } else {
            alert('❌ Failed to reset settings: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error resetting settings:', error);
        alert('❌ Error resetting settings: ' + error.message);
    }
}

// ============== PRO FEATURES ==============
let abortController = null;
let isGenerating = false;

function stopGeneration() {
    if (abortController) {
        abortController.abort();
        abortController = null;
    }
    isGenerating = false;

    // Update UI
    const stopBtn = document.getElementById('stop-btn');
    const sendBtn = document.getElementById('send-btn');

    if (stopBtn) stopBtn.classList.add('hidden');
    if (sendBtn) sendBtn.classList.remove('sending');

    // Add interrupted message
    const chatHistory = document.getElementById('chat-history');
    if (chatHistory) {
        const lastMsg = chatHistory.querySelector('.bot-message:last-child');
        if (lastMsg && !lastMsg.textContent.includes('[Generation stopped]')) {
            lastMsg.innerHTML += '<br><em style="color: #a1a1aa;">[Generation stopped]</em>';
        }
    }
}

function toggleCitations() {
    const panel = document.getElementById('citations-panel');
    if (panel) {
        panel.classList.toggle('hidden');
    }
}

function showCitations(sources) {
    const panel = document.getElementById('citations-panel');
    const list = document.getElementById('citations-list');

    if (!panel || !list || !sources || sources.length === 0) return;

    list.innerHTML = '';

    sources.forEach((source, index) => {
        const item = document.createElement('div');
        item.className = 'citation-item';

        const filename = source.source || source.filename || `Source ${index + 1}`;
        const snippet = source.content ? source.content.substring(0, 100) + '...' : '';
        const ext = filename.split('.').pop().toUpperCase();

        item.innerHTML = `
            <div class="citation-icon">${ext}</div>
            <div class="citation-info">
                <div class="citation-name">${filename}</div>
                <div class="citation-snippet">${snippet}</div>
            </div>
        `;

        item.onclick = () => {
            // Could open file preview or highlight in file manager
            console.log('Citation clicked:', source);
        };

        list.appendChild(item);
    });

    panel.classList.remove('hidden');
}

// ============== STATS & LOADING ==============
async function loadStats() {
    const ids = ['stat-docs', 'stat-chunks', 'stat-sessions', 'stat-messages'];
    ids.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.add('skeleton');
    });

    try {
        const response = await fetch('/api/stats');
        const data = await response.json();

        // Check for Empty State (No documents indexed)
        const isEmpty = (data.total_documents || 0) === 0 && (data.total_messages || 0) === 0;
        const emptyState = document.getElementById('dashboard-empty-state');
        const dashboard = document.getElementById('dashboard-view');

        if (dashboard && emptyState) {
            if (isEmpty) {
                // Hide content, show empty state
                Array.from(dashboard.children).forEach(child => {
                    if (!child.classList.contains('empty-state')) child.classList.add('hidden');
                });
                emptyState.classList.remove('hidden');
            } else {
                // Show content, hide empty state
                Array.from(dashboard.children).forEach(child => {
                    if (!child.classList.contains('empty-state')) child.classList.remove('hidden');
                });
                emptyState.classList.add('hidden');
            }
        }

        if (document.getElementById('stat-docs')) document.getElementById('stat-docs').innerText = data.total_documents || 0;
        if (document.getElementById('stat-chunks')) document.getElementById('stat-chunks').innerText = data.total_chunks || 0;
        if (document.getElementById('stat-sessions')) document.getElementById('stat-sessions').innerText = data.total_sessions || 0;
        if (document.getElementById('stat-messages')) document.getElementById('stat-messages').innerText = data.total_messages || 0;

        if (window.usageChart && window.usageChart.data) {
            window.usageChart.data.datasets[0].data = [
                data.total_documents,
                data.total_chunks,
                data.total_sessions,
                data.total_messages
            ];
            window.usageChart.update();
        }
    } catch (e) {
        console.error('Failed to load stats:', e);
    } finally {
        ids.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.classList.remove('skeleton');
        });
    }
}

// ============== FILE MANAGEMENT ==============
async function loadFiles() {
    const container = document.getElementById('file-grid');
    if (!container) return;

    if (container.children.length === 0) {
        container.innerHTML = Array(3).fill(0).map(() => `
            <div class="file-card">
                <div class="file-icon skeleton" style="width: 40px; height: 40px;"></div>
                <div class="file-info" style="width: 100%">
                    <div class="file-name skeleton" style="width: 80%; margin-bottom: 5px;"></div>
                    <div class="file-meta skeleton" style="width: 50%;"></div>
                </div>
            </div>
        `).join('');
    }

    try {
        const response = await fetch('/api/files');
        const data = await response.json();
        renderFiles(data.files || []);
    } catch (e) {
        console.error('Failed to load files:', e);
        container.innerHTML = '<div class="empty-state"><p>Failed to load files</p></div>';
    }
}

function renderFiles(files) {
    const container = document.getElementById('file-grid');
    container.className = fileViewMode === 'grid' ? 'file-grid' : 'file-list';

    const bulkActions = document.getElementById('bulk-actions');
    if (bulkActions) bulkActions.style.display = 'none';

    const emptyState = document.getElementById('files-empty-state');
    const fileContainer = document.getElementById('file-container');

    if (files.length === 0) {
        if (emptyState) emptyState.classList.remove('hidden');
        if (fileContainer) fileContainer.classList.add('hidden');
        container.innerHTML = '';
        return;
    } else {
        if (emptyState) emptyState.classList.add('hidden');
        if (fileContainer) fileContainer.classList.remove('hidden');
    }

    container.innerHTML = files.map(file => `
        <div class="file-card" 
             oncontextmenu="showContextMenu(event, 'indexed', '${file.name}')"
             ondblclick="showPreview('${file.name}')">
            
            <div class="file-icon">${getFileIcon(file.name)}</div>
            <div class="file-info">
                <div class="file-name" title="${file.name}">${file.name}</div>
                <div class="file-meta">${formatFileSize(file.size)} • ${formatDate(file.modified)}</div>
            </div>
        </div>
    `).join('');
}

// Ensure no old functions leak
window.renderFiles = renderFiles;

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
    try {
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

// ============== FILE PREVIEW ==============
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

// ============== VIEW NAVIGATION ==============
var showView = function (viewId) {
    localStorage.setItem('lastView', viewId);
    document.querySelectorAll('.view-section').forEach(el => el.classList.add('hidden'));
    document.getElementById('input-bar').classList.add('hidden');

    let targetId = viewId + '-view';
    if (viewId === 'controls') targetId = 'control-panel';
    if (viewId === 'dashboard') targetId = 'dashboard-view';
    if (viewId === 'files') targetId = 'files-view';
    if (viewId === 'chat') targetId = 'chat-view';
    if (viewId === 'settings') targetId = 'settings-view';

    const target = document.getElementById(targetId);
    if (target) target.classList.remove('hidden');

    // Update Nav Buttons
    document.querySelectorAll('.rail-btn').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.getElementById(`nav-btn-${viewId}`);
    if (activeBtn) activeBtn.classList.add('active');

    if (viewId === 'files') loadFiles();
    if (viewId === 'dashboard') loadStats();
    if (viewId === 'chat') {
        document.getElementById('input-bar').classList.remove('hidden');
        scrollToBottom();
    }
};

// ============== HELPERS ==============
function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    // Icons8 icon URLs for file types
    const icons = {
        'pdf': '<img src="https://img.icons8.com/?id=299&format=png&size=24" class="icon file-icon" alt="PDF">',
        'doc': '<img src="https://img.icons8.com/?id=11571&format=png&size=24" class="icon file-icon" alt="DOC">',
        'docx': '<img src="https://img.icons8.com/?id=11571&format=png&size=24" class="icon file-icon" alt="DOCX">',
        'txt': '<img src="https://img.icons8.com/?id=2290&format=png&size=24" class="icon file-icon" alt="TXT">',
        'md': '<img src="https://img.icons8.com/?id=21812&format=png&size=24" class="icon file-icon" alt="MD">',
        'json': '<img src="https://img.icons8.com/?id=22441&format=png&size=24" class="icon file-icon" alt="JSON">',
        'csv': '<img src="https://img.icons8.com/?id=2577&format=png&size=24" class="icon file-icon" alt="CSV">',
        'xls': '<img src="https://img.icons8.com/?id=11566&format=png&size=24" class="icon file-icon" alt="XLS">',
        'xlsx': '<img src="https://img.icons8.com/?id=11566&format=png&size=24" class="icon file-icon" alt="XLSX">',
        'png': '<img src="https://img.icons8.com/?id=11561&format=png&size=24" class="icon file-icon" alt="PNG">',
        'jpg': '<img src="https://img.icons8.com/?id=11561&format=png&size=24" class="icon file-icon" alt="JPG">',
        'jpeg': '<img src="https://img.icons8.com/?id=11561&format=png&size=24" class="icon file-icon" alt="JPEG">',
        'gif': '<img src="https://img.icons8.com/?id=11561&format=png&size=24" class="icon file-icon" alt="GIF">',
        'py': '<img src="https://img.icons8.com/?id=12584&format=png&size=24" class="icon file-icon" alt="Python">',
        'js': '<img src="https://img.icons8.com/?id=39853&format=png&size=24" class="icon file-icon" alt="JS">',
        'html': '<img src="https://img.icons8.com/?id=1043&format=png&size=24" class="icon file-icon" alt="HTML">',
        'css': '<img src="https://img.icons8.com/?id=1045&format=png&size=24" class="icon file-icon" alt="CSS">'
    };
    return icons[ext] || '<img src="https://img.icons8.com/?id=1395&format=png&size=24" class="icon file-icon" alt="File">';
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

// ==========================================
// SEARCH & FILTER LOGIC
// ==========================================

function filterSidebarSessions() {
    const query = document.getElementById('sidebar-search').value.toLowerCase();
    const sessions = document.querySelectorAll('.session-item');

    sessions.forEach(item => {
        const name = item.innerText.toLowerCase();
        if (name.includes(query)) {
            item.style.display = 'flex';
        } else {
            item.style.display = 'none';
        }
    });
}

function handleGlobalSearch(event) {
    if (event.key === 'Enter') {
        const query = document.getElementById('global-search-input').value;
        if (query.length > 1) {
            performSearch(query);
        }
    }
}

async function performSearch(query) {
    const modal = document.getElementById('search-modal');
    const container = document.getElementById('search-results-body');

    modal.style.display = 'flex';
    container.innerHTML = '<div style="padding:20px; text-align:center;">Scanning databanks...</div>';

    try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        const data = await res.json();
        renderSearchResults(data);
    } catch (e) {
        container.innerHTML = '<div style="padding:20px; text-align:center; color: var(--error-color);">Search failed. System overload.</div>';
    }
}

function renderSearchResults(data) {
    const container = document.getElementById('search-results-body');
    container.innerHTML = '';

    if (data.sessions.length === 0 && data.messages.length === 0 && data.files.length === 0) {
        container.innerHTML = '<div style="padding:20px; text-align:center; color: var(--text-muted);">No matching data found.</div>';
        return;
    }

    // Helper to create category section
    const createSection = (title, items, icon, renderItem) => {
        if (items.length === 0) return '';
        let html = `<h4 style="background: rgba(255,255,255,0.05); padding: 10px 20px; margin: 0; border-bottom: 1px solid var(--border-color);">${icon} ${title} (${items.length})</h4>`;
        html += '<div style="display: flex; flex-direction: column;">';
        items.forEach(item => {
            html += renderItem(item);
        });
        html += '</div>';
        return html;
    };

    // Sessions
    container.innerHTML += createSection("Sessions", data.sessions, "💬", (s) => `
        <div onclick="switchSession(${s.id}); document.getElementById('search-modal').style.display='none'; showView('chat');" 
             style="padding: 12px 20px; border-bottom: 1px solid var(--border-color); cursor: pointer; hover: background: rgba(255,255,255,0.02);">
            <div style="font-weight: 500; color: var(--text-color);">${s.name}</div>
            <div style="font-size: 0.8em; color: var(--text-secondary);">Last active: ${s.updated_at}</div>
        </div>
    `);

    // Messages
    container.innerHTML += createSection("Messages", data.messages, "📨", (m) => `
        <div onclick="switchSession(${m.session_id}); document.getElementById('search-modal').style.display='none'; showView('chat');" 
             style="padding: 12px 20px; border-bottom: 1px solid var(--border-color); cursor: pointer;">
            <div style="font-size: 0.9em; color: var(--text-muted); margin-bottom: 4px;">In: ${m.session_name || 'Unknown Chat'}</div>
            <div style="color: var(--text-color); line-height: 1.4;">${escapeHtml(m.content).substring(0, 150)}${m.content.length > 150 ? '...' : ''}</div>
        </div>
    `);

    // Files
    container.innerHTML += createSection("Files", data.files, "📄", (f) => `
        <div onclick="document.getElementById('search-modal').style.display='none'; showView('files');" 
             style="padding: 12px 20px; border-bottom: 1px solid var(--border-color); cursor: pointer;">
            <div style="color: var(--text-color);">${f}</div>
        </div>
    `);
}

function openPromptLibrary() {
    const modal = document.getElementById('prompt-modal');
    modal.style.display = 'flex';
    loadPrompts();
}

async function loadPrompts() {
    const container = document.getElementById('prompt-list');
    try {
        const res = await fetch('/api/prompts');
        const prompts = await res.json();

        container.innerHTML = '';
        if (prompts.length === 0) {
            container.innerHTML = '<div style="text-align: center; color: var(--text-muted);">No prompts saved yet. Create one above!</div>';
            return;
        }

        prompts.forEach(p => {
            const card = document.createElement('div');
            card.style.cssText = 'background: var(--card-bg); border: 1px solid var(--border-color); padding: 12px; border-radius: 8px; position: relative;';
            card.innerHTML = `
                <div style="font-weight: 600; margin-bottom: 5px; display: flex; justify-content: space-between;">
                    <span>${p.title}</span>
                    <button onclick="deletePrompt(${p.id})" style="color: var(--error-color); background: none; border: none; cursor: pointer;">🗑️</button>
                </div>
                <div style="font-size: 0.9em; color: var(--text-secondary); max-height: 60px; overflow: hidden; margin-bottom: 10px;">${p.content}</div>
                <button class="secondary-btn" onclick="usePrompt('${p.content.replace(/'/g, "\\'")}')" style="width: 100%; padding: 6px; font-size: 0.9em;">Use This Prompt</button>
            `;
            container.appendChild(card);
        });
    } catch (e) {
        container.innerHTML = '<div style="color: var(--error-color);">Error loading prompts.</div>';
    }
}

async function savePrompt() {
    const title = document.getElementById('new-prompt-title').value;
    const content = document.getElementById('new-prompt-content').value;

    if (!title || !content) {
        alert("Please fill in both title and content.");
        return;
    }

    try {
        await fetch('/api/prompts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, content })
        });
        document.getElementById('new-prompt-title').value = '';
        document.getElementById('new-prompt-content').value = '';
        loadPrompts(); // Refresh list
    } catch (e) {
        alert("Failed to save prompt.");
    }
}

async function deletePrompt(id) {
    if (!confirm("Delete this prompt?")) return;
    await fetch(`/api/prompts/${id}`, { method: 'DELETE' });
    loadPrompts();
}

function usePrompt(content) {
    document.getElementById('prompt-modal').style.display = 'none';
    showView('chat');
    // Set content to input box
    const input = document.getElementById('message-input');
    input.value = content;
    input.focus();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    let icon = type === 'error' ? '❌' : type === 'success' ? '✅' : type === 'warning' ? '⚠️' : 'ℹ️';
    toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.5s ease-out forwards';
        setTimeout(() => toast.remove(), 500);
    }, 3000);
}

// Override default alert
window.alert = function (msg) { showToast(msg, 'warning'); };

// ============== CONTEXT MENU ==============
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

// Session Context Menu
function showSessionContextMenu(event, sessionId, sessionName) {
    event.preventDefault();
    event.stopPropagation();

    const menu = document.getElementById('context-menu');
    menu.innerHTML = `
        <div class="context-menu-item" onclick="exportSession(${sessionId}, '${sessionName}', 'txt')">
            📄 Export as TXT
        </div>
        <div class="context-menu-item" onclick="exportSession(${sessionId}, '${sessionName}', 'md')">
            📝 Export as Markdown
        </div>
        <div class="context-menu-divider"></div>
        <div class="context-menu-item danger" onclick="deleteSession(${sessionId}, event)">
            🗑️ Delete
        </div>
    `;

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

async function exportSession(sessionId, sessionName, format) {
    // Hide context menu
    const menu = document.getElementById('context-menu');
    if (menu) {
        menu.classList.remove('visible');
        menu.style.display = 'none';
    }

    // Trigger download via backend endpoint
    window.location.href = `/api/sessions/${sessionId}/export?format=${format}`;
    showToast(`Exporting as ${format.toUpperCase()}...`, 'info');
}

// ============== HEALTH CHECK ==============
async function checkHealth() {
    const dot = document.getElementById('status-dot');
    const text = document.getElementById('status-text');
    if (!dot) return;

    dot.className = 'status-dot loading';
    text.innerText = 'Checking...';

    try {
        const response = await fetch('/api/health');
        const data = await response.json();

        if (data.ollama && data.ollama.available) {
            dot.className = 'status-dot';
            text.innerText = 'Connected';
        } else {
            dot.className = 'status-dot offline';
            text.innerText = 'Offline';
        }
    } catch (e) {
        dot.className = 'status-dot offline';
        text.innerText = 'Error';
    }
}

function toggleMode() {
    const btn = document.getElementById('btn-toggle');
    const status = document.getElementById('mode-status');

    if (currentMode === 'cli') {
        currentMode = 'browser';
        btn.innerHTML = '<img src="https://img.icons8.com/?id=2177&format=png&size=24" class="icon" alt="CLI"> CLI Mode';
        if (status) status.innerHTML = 'Mode: <strong>Browser Chat</strong>';
        showView('chat');
    } else {
        currentMode = 'cli';
        btn.innerHTML = '<img src="https://img.icons8.com/?id=38977&format=png&size=24" class="icon" alt="Chat"> Chat Mode';
        if (status) status.innerHTML = 'Mode: <strong>CLI Chat</strong>';
        showView('controls');
    }

    fetch('/set_mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: currentMode })
    }).catch(console.error);
}

// ============== CHAT & SESSION MANAGEMENT ==============
async function loadSessions() {
    try {
        const response = await fetch('/api/sessions');
        const data = await response.json();
        const sessions = data.sessions || [];
        const list = document.getElementById('session-list');
        if (!list) return;

        // Update currentSessionId from server if not set
        if (!currentSessionId && data.current) {
            currentSessionId = data.current;
        }

        list.innerHTML = sessions.map(session => `
            <div class="history-item ${session.id === currentSessionId ? 'active' : ''}" 
                 onclick="switchSession(${session.id})"
                 oncontextmenu="showSessionContextMenu(event, ${session.id}, '${session.name.replace(/'/g, "\\'")}')"
                 title="${session.name}">
                <span class="history-name">${session.name}</span>
                <button class="delete-session-btn" onclick="deleteSession(${session.id}, event)" title="Delete Session">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="#e74c3c">
                        <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM8 9h8v10H8V9zm7.5-5l-1-1h-5l-1 1H5v2h14V4h-3.5z"/>
                        <path d="M9 12h2v5H9zm4 0h2v5h-2z" fill="white"/>
                    </svg>
                </button>
            </div>
        `).join('');
    } catch (e) {
        console.error('Failed to load sessions:', e);
    }
}


function newChat() {
    // Lazy session creation - don't create in DB until first message is sent
    currentSessionId = null;

    // Clear chat UI
    const historyContainer = document.getElementById('chat-history');
    if (historyContainer) {
        historyContainer.innerHTML = '';
    }

    // Show Empty State
    const emptyState = document.getElementById('chat-empty-state');
    if (emptyState) emptyState.style.display = 'flex';

    // Update sidebar to show no active session
    document.querySelectorAll('.history-item').forEach(item => {
        item.classList.remove('active');
    });

    showView('chat');
    showToast('New chat ready', 'success');
}

async function switchSession(id) {
    currentSessionId = id;
    await loadSessions(); // Refresh active class
    await loadChatHistory();
    showView('chat');
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


// Helper for empty state toggling
function toggleEmptyState(show) {
    const emptyState = document.getElementById('chat-empty-state');
    if (!emptyState) return;

    if (show) {
        emptyState.classList.remove('hidden');
        emptyState.style.display = 'flex';
    } else {
        emptyState.classList.add('hidden');
        emptyState.style.display = 'none';
    }
}

async function loadChatHistory() {
    if (!currentSessionId) return;
    const sessionId = parseInt(currentSessionId);
    console.log('Loading chat history for session:', sessionId);

    const historyContainer = document.getElementById('chat-history');
    if (!historyContainer) return;

    // Clear current content but keep structure
    // historyContainer.innerHTML = '<div class="loading">Loading history...</div>'; // removed to prevent flicker

    try {
        const url = `/api/sessions/${sessionId}`;
        console.log('Fetching:', url);
        const response = await fetch(url);
        console.log('Response status:', response.status);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }


        const data = await response.json();
        console.log('Response data:', data);

        if (data.messages && data.messages.length > 0) {
            toggleEmptyState(false);
            historyContainer.innerHTML = data.messages.map(msg => `
                <div class="chat-message ${msg.role}-message">
                    <div class="message-content">${msg.role === 'assistant' ? (typeof marked !== 'undefined' ? marked.parse(msg.content) : msg.content) : msg.content}</div>
                    <div class="message-meta">${new Date(msg.created_at).toLocaleTimeString()}</div>
                </div>
            `).join('');
        } else {
            toggleEmptyState(true);
            historyContainer.innerHTML = '';
        }
        scrollToBottom();
    } catch (e) {
        console.error('loadChatHistory error:', e);
        historyContainer.innerHTML = '<div class="error-message">Failed to load history</div>';
    }
}


async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;

    if (!currentSessionId) {
        // Create session on first message (lazy creation)
        try {
            const response = await fetch('/api/sessions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: message.substring(0, 50) })
            });
            const data = await response.json();
            if (data.session_id) {
                currentSessionId = data.session_id;
                loadSessions();
            }
        } catch (e) {
            showToast('Failed to create session', 'error');
            return;
        }
    }

    input.value = '';
    input.disabled = true;

    // Immediately hide empty state
    toggleEmptyState(false);

    const historyContainer = document.getElementById('chat-history');

    // Remove empty state placeholder if present (old code legacy)
    const oldPlaceholder = historyContainer.querySelector('.empty-state');
    if (oldPlaceholder) oldPlaceholder.remove();

    // Add user message visually
    historyContainer.innerHTML += `<div class="chat-message user-message"><div class="message-content">${escapeHtml(message)}</div></div>`;

    // Add bot message container
    const botMsgDiv = document.createElement('div');
    botMsgDiv.className = 'chat-message bot-message';
    botMsgDiv.innerHTML = '<div class="message-content"><span class="loading-spinner"></span> Thinking...</div>';
    historyContainer.appendChild(botMsgDiv);
    scrollToBottom();

    const startTime = performance.now();
    isGenerating = true;

    // Show stop button
    const stopBtn = document.getElementById('stop-btn');
    const sendBtn = document.getElementById('send-btn');
    if (stopBtn) stopBtn.classList.remove('hidden');
    if (sendBtn) sendBtn.classList.add('sending');

    try {
        abortController = new AbortController();
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message, // Changed from question to message to match backend
                session_id: currentSessionId
            }),
            signal: abortController.signal
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = '';
        const contentDiv = botMsgDiv.querySelector('.message-content');
        contentDiv.innerHTML = ''; // Clear "Thinking..."

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            fullText += chunk;

            // Live render markdown (debounced in production, but direct here is fine for now)
            contentDiv.innerHTML = typeof marked !== 'undefined' ? marked.parse(fullText) : escapeHtml(fullText);

            // Auto scroll only if near bottom
            // scrollToBottom(); 
            // Better: scroll current message into view
            botMsgDiv.scrollIntoView({ behavior: "smooth", block: "end" });
        }

        const endTime = performance.now();
        const duration = ((endTime - startTime) / 1000).toFixed(1);

        // Add metrics footer
        let metricsHtml = `<div class="message-meta">${duration}s`;
        metricsHtml += ` • AI</div>`;
        botMsgDiv.insertAdjacentHTML('beforeend', metricsHtml);

        // Highlight code blocks
        if (typeof hljs !== 'undefined') {
            botMsgDiv.querySelectorAll('pre code').forEach(block => hljs.highlightElement(block));
        }

    } catch (e) {
        if (e.name === 'AbortError') {
            botMsgDiv.insertAdjacentHTML('beforeend', '<br><em style="color: #a1a1aa;">[Generation stopped]</em>');
        } else {
            botMsgDiv.innerHTML += `<div class="error-message">Error: ${e.message}</div>`;
            showToast('Generation failed', 'error');
        }
    } finally {
        isGenerating = false;
        abortController = null;
        input.disabled = false;
        input.focus();

        if (stopBtn) stopBtn.classList.add('hidden');
        if (sendBtn) sendBtn.classList.remove('sending');

        // Do NOT reload history immediately to prevent race condition
        // loadChatHistory(); 
        await loadSessions(); // Update session list order/preview
    }
}

function scrollToBottom() {
    const history = document.getElementById('chat-history');
    history.scrollTop = history.scrollHeight;
}

// ============== INDEX MANAGEMENT ==============
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

// Set Mode Function
async function setMode(mode) {
    try {
        const response = await fetch('/set_mode', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: mode })
        });
        const data = await response.json();

        if (data.status === 'success' || response.ok) {
            // Update UI
            const modeDisplay = document.getElementById('current-mode');
            const modeStatus = document.getElementById('mode-status');
            if (modeDisplay) modeDisplay.textContent = mode === 'browser' ? 'Browser' : 'CLI';
            if (modeStatus) modeStatus.innerHTML = `Mode: <strong>${mode === 'browser' ? 'Browser Chat' : 'CLI Chat'}</strong>`;

            // Update button states
            document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active'));
            document.getElementById(`${mode}-mode-btn`)?.classList.add('active');

            showToast(`Switched to ${mode === 'browser' ? 'Browser' : 'CLI'} mode`, 'success');
        } else {
            showToast('Failed to switch mode', 'error');
        }
    } catch (e) {
        showToast('Error switching mode: ' + e.message, 'error');
    }
}

function setFileView(mode) {
    fileViewMode = mode;
    loadFiles(); // Re-render

    // Update buttons
    document.querySelectorAll('.view-toggle button').forEach(btn => btn.classList.remove('active'));
    if (mode === 'grid') document.getElementById('grid-view-btn')?.classList.add('active');
    if (mode === 'list') document.getElementById('list-view-btn')?.classList.add('active');
}

// ============== SIDEBAR RESIZE ==============
function initSidebarResize() {
    const sidebar = document.querySelector('.sidebar');
    const handle = document.getElementById('sidebar-resize-handle');
    if (!sidebar || !handle) return;

    const MIN_WIDTH = 180;
    const MAX_WIDTH = 400;
    let isResizing = false;

    // Load saved width
    const savedWidth = localStorage.getItem('sidebarWidth');
    if (savedWidth) {
        const width = parseInt(savedWidth);
        if (width >= MIN_WIDTH && width <= MAX_WIDTH) {
            sidebar.style.width = width + 'px';
        }
    }


    handle.addEventListener('mousedown', function (e) {
        if (e.button !== 0) return; // Only left click
        isResizing = true;
        handle.classList.add('active');
        document.body.style.cursor = 'ew-resize';
        document.body.style.userSelect = 'none';
        e.preventDefault();
    });

    window.addEventListener('mousemove', function (e) {
        if (!isResizing) return;
        const newWidth = e.clientX;
        if (newWidth >= MIN_WIDTH && newWidth <= MAX_WIDTH) {
            sidebar.style.width = newWidth + 'px';
        }
    });

    window.addEventListener('mouseup', function () {
        if (isResizing) {
            isResizing = false;
            handle.classList.remove('active');
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
            // Save width to localStorage
            localStorage.setItem('sidebarWidth', sidebar.offsetWidth);
        }
    });
}

// ============== INITIALIZATION ==============
function initApp(configMode, sessionId) {
    // Set globals from template
    currentMode = configMode || 'cli';
    currentSessionId = sessionId;

    // Restore theme
    // Restore theme
    // Load Compact Mode
    if (localStorage.getItem('compactMode') === 'true') {
        document.body.classList.add('compact-mode');
        const toggle = document.getElementById('compact-mode-toggle');
        if (toggle) toggle.checked = true;
    }

    // Init Graph if on dashboard
    if (document.getElementById('knowledge-graph')) {
        initGraphPlaceholder();
    }

    // Load initial data
    loadSessions();
    checkHealth();

    // Show default view
    const lastView = localStorage.getItem('lastView');
    showView(lastView || 'dashboard');

    // Initialize sidebar resize
    initSidebarResize();

    // Move context menu to body
    const menu = document.getElementById('context-menu');
    if (menu && menu.parentNode !== document.body) {
        document.body.appendChild(menu);
    }

    // Periodic health check
    setInterval(checkHealth, 30000);

    // Enter key listener for chat
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }


    // Initialize Charts
    initDashboardCharts();

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        document.body.addEventListener(eventName, function (e) {
            e.preventDefault();
            e.stopPropagation();
        }, false);
    });
}


// ============== DASHBOARD CHARTS ==============
function initDashboardCharts() {
    const tokenCtx = document.getElementById('tokenChart');
    const typesCtx = document.getElementById('typesChart');

    if (typeof Chart === 'undefined') return;

    // 1. Token Usage - Line Chart (Visual Only - Mock Data)
    if (tokenCtx) {
        window.tokenChart = new Chart(tokenCtx, {
            type: 'line',
            data: {
                labels: ['10:00', '10:05', '10:10', '10:15', '10:20', '10:25', '10:30'],
                datasets: [{
                    label: 'Tokens',
                    data: [150, 230, 180, 320, 290, 450, 410],
                    borderColor: '#3b82f6',
                    backgroundColor: (context) => {
                        const ctx = context.chart.ctx;
                        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
                        gradient.addColorStop(0, 'rgba(59, 130, 246, 0.5)');
                        gradient.addColorStop(1, 'rgba(59, 130, 246, 0.0)');
                        return gradient;
                    },
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 0,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#a1a1aa' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#a1a1aa' }
                    }
                },
                interaction: {
                    mode: 'index',
                    intersect: false,
                }
            }
        });
    }

    // 2. Knowledge Distribution - Doughnut Chart
    if (typesCtx) {
        window.typesChart = new Chart(typesCtx, {
            type: 'doughnut',

            data: {
                labels: ['PDF', 'TXT', 'MD', 'Code'],
                datasets: [{
                    data: [35, 25, 20, 20],
                    backgroundColor: [
                        '#3b82f6', // Blue
                        '#22c55e', // Green
                        '#a855f7', // Purple
                        '#f97316'  // Orange
                    ],
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: {
                cutout: '75%',
                plugins: { legend: { display: false } }, // Clean look
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }
}

// Global Polling for Sync
setInterval(async function () {
    try {
        const response = await fetch('/api/settings');
        const config = await response.json();

        // 1. Update Mode UI (Block/Unblock)
        const isCli = config.mode === 'cli';
        const inputBar = document.getElementById('input-bar');
        const chatContainer = document.getElementById('chat-view'); // Fixed: match HTML ID
        const statusEl = document.getElementById('mode-status');

        if (statusEl) {
            statusEl.innerHTML = `Mode: <strong>${isCli ? 'CLI Chat' : 'Browser Chat'}</strong>`;
        }

        if (inputBar) {
            if (isCli) {
                inputBar.classList.add('disabled');
                inputBar.style.opacity = '0.5';
                inputBar.style.pointerEvents = 'none';

                if (!document.getElementById('cli-overlay') && chatContainer) {
                    const overlay = document.createElement('div');
                    overlay.id = 'cli-overlay';
                    overlay.innerHTML = '<div style="background:rgba(0,0,0,0.85); padding:24px; border-radius:12px; color:white; text-align:center; border: 1px solid rgba(255,255,255,0.1); backdrop-filter: blur(8px);"><h3>CLI Chat Mode Active</h3><p style="margin: 10px 0; font-size: 1.1em; color: #a1a1aa;">Chat in CLI.</p><button class="secondary-btn" onclick="setMode(\'browser\')" style="margin-top: 10px;">Switch to Browser Mode</button></div>';
                    overlay.style.position = 'absolute';
                    overlay.style.top = '50%';
                    overlay.style.left = '50%';
                    overlay.style.transform = 'translate(-50%, -50%)';
                    overlay.style.zIndex = '1000';
                    overlay.style.width = '100%';
                    overlay.style.height = '100%';
                    overlay.style.display = 'flex';
                    overlay.style.justifyContent = 'center';
                    overlay.style.alignItems = 'center';
                    chatContainer.style.position = 'relative';
                    chatContainer.appendChild(overlay);
                }
            } else {
                inputBar.classList.remove('disabled');
                inputBar.style.opacity = '1';
                inputBar.style.pointerEvents = 'auto'; // Fixed: 'all' is not standard for HTML
                const overlay = document.getElementById('cli-overlay');
                if (overlay) overlay.remove();
            }
        }

        if (!document.getElementById('chat-view').classList.contains('hidden')) {
            await syncChatHistory();
        }

    } catch (e) {
        console.error("Error polling status:", e);
    }
}, 2000);

// Global State for Sync
let lastMessageCount = 0;

async function syncChatHistory() {
    try {
        const sessionId = localStorage.getItem('currentSessionId');
        if (!sessionId) return;

        const response = await fetch(`/api/sessions/${sessionId}`);
        const data = await response.json();

        if (data.messages && data.messages.length > lastMessageCount) {
            // If this is the initial load, just set the count
            if (lastMessageCount === 0) {
                lastMessageCount = data.messages.length;
                return;
            }

            // Append new messages
            const newMessages = data.messages.slice(lastMessageCount);
            const chatHistory = document.getElementById('chat-history');

            newMessages.forEach(msg => {
                const div = document.createElement('div');
                div.className = `chat-message ${msg.role}-message`;
                const content = marked.parse(msg.content);
                div.innerHTML = `<div class="message-content">${content}</div>`;
                chatHistory.appendChild(div);
            });

            lastMessageCount = data.messages.length;
            scrollToBottom();
        }
    } catch (e) {
        // console.warn("Sync error:", e);
    }
}


// ============== ACTIVITY FEED ==============
function addActivity(text, icon = 'doc') {
    const feed = document.getElementById('activity-feed');
    if (!feed) return;

    const iconUrls = {
        'doc': 'https://img.icons8.com/?id=1395&format=png&size=16',
        'chat': 'https://img.icons8.com/?id=38977&format=png&size=16',
        'upload': 'https://img.icons8.com/?id=368&format=png&size=16',
        'success': 'https://img.icons8.com/?id=11695&format=png&size=16'
    };

    const item = document.createElement('div');
    item.className = 'activity-item';
    item.innerHTML = `
        <div class="activity-icon"><img src="${iconUrls[icon] || iconUrls.doc}" class="icon" alt="${icon}"></div>
        <span class="activity-text">${text}</span>
        <span class="activity-time">Just now</span>
    `;

    // Add to top
    feed.insertBefore(item, feed.firstChild);

    // Keep only last 5 items
    while (feed.children.length > 5) {
        feed.removeChild(feed.lastChild);
    }
}

// ==========================================
// SESSION RENAME LOGIC
// ==========================================
let currentRenameSessionId = null;

function openRenameModal(sessionId, currentName) {
    currentRenameSessionId = sessionId;
    const input = document.getElementById('rename-input');
    // Decode escaped quotes
    input.value = currentName;

    document.getElementById('rename-modal').style.display = 'flex';
    input.focus();

    // Bind Enter/Esc
    input.onkeydown = (e) => {
        if (e.key === 'Enter') submitRename();
        if (e.key === 'Escape') closeRenameModal();
    };

    // Bind Confirm
    document.getElementById('rename-confirm-btn').onclick = submitRename;
}

function closeRenameModal() {
    document.getElementById('rename-modal').style.display = 'none';
    currentRenameSessionId = null;
    const input = document.getElementById('rename-input');
    if (input) input.onkeydown = null;
}

async function submitRename() {
    if (!currentRenameSessionId) return;
    const newName = document.getElementById('rename-input').value.trim();
    console.log('[DEBUG] Submitting rename for:', currentRenameSessionId, 'New Name:', newName);

    if (!newName) {
        showToast('Please enter a name', 'warning');
        return;
    }

    try {
        const response = await fetch(`/api/sessions/${currentRenameSessionId}/rename`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: newName })
        });

        const data = await response.json();

        if (data.success) {
            // Refresh session list to show new name safely
            await loadSessions();
            showToast('Renamed successfully', 'success');
            closeRenameModal();
        } else {
            showToast(data.error || 'Rename failed', 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Error renaming session', 'error');
    }
}
