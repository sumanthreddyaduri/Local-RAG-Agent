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
let currentMode = 'cli';
let currentSessionId = null;
let lastMessageId = 0; // START: Real-time Sync Track

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

// ============== THEME & UI ==============
function setTheme(mode) {
    localStorage.setItem('theme', mode);

    const selector = document.getElementById('theme-selector');
    if (selector && selector.value !== mode) selector.value = mode;

    let isDark = false;
    if (mode === 'auto') {
        isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    } else {
        isDark = mode === 'dark';
    }

    if (isDark) {
        document.body.classList.add('dark-theme');
    } else {
        document.body.classList.remove('dark-theme');
    }
    updateThemeIcon(isDark);
}

function updateThemeIcon(isDark) {
    const icon = document.getElementById('theme-icon');
    if (icon) {
        icon.textContent = isDark ? '☀️' : '🌙';
    }
}

function toggleTheme() {
    // Legacy toggle support
    const current = localStorage.getItem('theme');
    const newMode = (current === 'dark') ? 'light' : 'dark';
    setTheme(newMode);
}

function setAccentColor(color, buttonElement) {
    // Update CSS custom property for accent color
    document.documentElement.style.setProperty('--accent-color', color);

    // Save to localStorage
    localStorage.setItem('accentColor', color);

    // Update active state on buttons
    const allColorButtons = document.querySelectorAll('.color-dot');
    allColorButtons.forEach(btn => {
        btn.classList.remove('active');
        btn.style.border = '2px solid white';
        btn.style.boxShadow = 'none';
    });

    // Set active state on clicked button
    if (buttonElement) {
        buttonElement.classList.add('active');
        buttonElement.style.border = '2px solid white';
        buttonElement.style.boxShadow = `0 0 0 2px ${color}`;
    }
}

function toggleCompactMode(isCompact) {
    if (isCompact) {
        document.body.classList.add('compact-mode');
        localStorage.setItem('compactMode', 'true');
    } else {
        document.body.classList.remove('compact-mode');
        localStorage.setItem('compactMode', 'false');
    }
}

function loadClientSettings() {
    // Theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);

    // System theme listener
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
        if (localStorage.getItem('theme') === 'auto') {
            if (e.matches) {
                document.body.classList.add('dark-theme');
                updateThemeIcon(true);
            } else {
                document.body.classList.remove('dark-theme');
                updateThemeIcon(false);
            }
        }
    });

    // Compact Mode
    const savedCompact = localStorage.getItem('compactMode') === 'true';
    toggleCompactMode(savedCompact);
    const compactToggle = document.getElementById('compact-mode-toggle');
    if (compactToggle) compactToggle.checked = savedCompact;

    // Accent Color
    const savedColor = localStorage.getItem('accentColor');
    if (savedColor) {
        document.documentElement.style.setProperty('--accent-color', savedColor);
    }
}

// ============== SETTINGS MANAGEMENT ==============
async function updateSetting(key, value) {
    // Permission Request for Desktop Notifications
    if (key === 'desktop_notifications' && value === true) {
        if (!('Notification' in window)) {
            showToast('❌ Browser does not support notifications', 'error');
            return;
        }
        const permission = await Notification.requestPermission();
        if (permission !== 'granted') {
            showToast('⚠️ Notification permission denied', 'warning');
            // Revert toggle if denied? Maybe too aggressive.
        } else {
            const n = new Notification('Onyx', { body: 'Desktop notifications enabled! 🔔' });
            setTimeout(() => n.close(), 3000);
        }
    }

    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ [key]: value })
        });
        const data = await response.json();
        if (data.status === 'success') {
            showToast(`Setting '${key}' updated`, 'success');
        } else {
            showToast('❌ Update failed: ' + (data.error || 'Unknown'), 'error');
            console.error('Failed to update setting:', data);
        }
    } catch (error) {
        showToast('❌ Error updating setting', 'error');
        console.error('Error updating setting:', error);
    }
}

async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        const config = await response.json();

        if (config) {
            const setVal = (id, val) => {
                const el = document.getElementById(id);
                if (el && val !== undefined && val !== null) el.value = val;
            };
            const setCheck = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.checked = !!val;
            };

            setVal('embed-model', config.embed_model);
            setVal('chunk-size', config.chunk_size);
            setVal('chunk-overlap', config.chunk_overlap);
            setVal('retrieval-k', config.retrieval_k);
            setCheck('hybrid-search', config.use_hybrid_search);
            setVal('hybrid-alpha', config.hybrid_alpha);
            setVal('max-history', config.max_history_context);
            setCheck('show-sources', config.show_sources);
            setCheck('tts-toggle', config.enable_tts);
            setVal('ollama-host', config.ollama_host);

            // Restore Theme from Server Config
            if (config.theme) {
                setTheme(config.theme);
            }

            // Update Mode UI (Merged from modules.js)
            const mode = config.mode || 'cli';
            if (typeof currentMode !== 'undefined') currentMode = mode;

            const modeBadge = document.getElementById('current-mode-badge');
            if (modeBadge) modeBadge.textContent = mode === 'browser' ? 'BROWSER' : 'CLI';

            const modeStatus = document.getElementById('mode-status');
            if (modeStatus) modeStatus.innerHTML = `Mode: <strong>${mode === 'browser' ? 'Browser Chat' : 'CLI Chat'}</strong>`;

            document.querySelectorAll('.mode-btn').forEach(btn => {
                btn.classList.remove('active');
                if (btn.dataset.mode === mode) btn.classList.add('active');
            });

            console.log('Settings loaded:', config);
        }
    } catch (e) {
        console.error('Failed to load settings:', e);
    }
}

async function saveAllSettings() {
    const saveBtn = document.querySelector('button[onclick="saveAllSettings()"]');
    const originalText = saveBtn ? saveBtn.innerText : 'Save Settings';
    if (saveBtn) {
        saveBtn.innerText = 'Saving...';
        saveBtn.disabled = true;
    }

    // Collect all settings from form inputs with EXPLICIT type conversion
    const settings = {
        embed_model: document.getElementById('embed-model')?.value,
        chunk_size: parseInt(document.getElementById('chunk-size')?.value) || 500,
        chunk_overlap: parseInt(document.getElementById('chunk-overlap')?.value) || 50,
        retrieval_k: parseInt(document.getElementById('retrieval-k')?.value) || 4,
        use_hybrid_search: document.getElementById('hybrid-search')?.checked || false,
        hybrid_alpha: parseFloat(document.getElementById('hybrid-alpha')?.value) || 0.5,
        max_history_context: parseInt(document.getElementById('max-history')?.value) || 10,
        show_sources: document.getElementById('show-sources')?.checked || false,
        enable_tts: document.getElementById('tts-toggle')?.checked || false,
        ollama_host: document.getElementById('ollama-host')?.value || "http://localhost:11434",
        notification_duration: parseInt(document.getElementById('notification-duration')?.value) || 3,
        theme: document.getElementById('theme-selector')?.value || 'dark'
    };

    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        const data = await response.json();

        if (data.status === 'success') {
            showToast('✅ Settings saved successfully!', 'success');
            // Optional: Update UI with sanitized values from server
            if (data.config) {
                // e.g. update fields if backend coerced values
            }
        } else {
            showToast('❌ Failed to save: ' + (data.details ? data.details.join(', ') : (data.error || 'Unknown error')), 'error');
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        showToast('❌ Network error saving settings', 'error');
    } finally {
        if (saveBtn) {
            saveBtn.innerText = originalText;
            saveBtn.disabled = false;
        }
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

        // Update Index Management Stats
        if (document.getElementById('mgmt-stat-docs')) {
            document.getElementById('mgmt-stat-docs').innerText = data.total_documents || 0;
            document.getElementById('mgmt-stat-chunks').innerText = data.total_chunks || 0;
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
function handleDragOver(event) {
    event.preventDefault();
    event.stopPropagation();
    const dropZone = document.getElementById('drop-zone');
    if (dropZone) dropZone.classList.add('drag-active');
}

function handleDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    const dropZone = document.getElementById('drop-zone');
    if (dropZone) dropZone.classList.remove('drag-active');

    if (event.dataTransfer.files && event.dataTransfer.files.length > 0) {
        addFilesToStage(event.dataTransfer.files);
    }
}

function handleFileSelect(event) {
    if (event.target.files && event.target.files.length > 0) {
        addFilesToStage(event.target.files);
    }
}

function addFilesToStage(files) {
    Array.from(files).forEach(file => {
        let exists = false;
        selectedFiles.forEach(f => {
            if (f.name === file.name) exists = true;
        });
        if (!exists) selectedFiles.add(file);
    });
    renderStagedFiles();
}

function renderStagedFiles() {
    const container = document.getElementById('file-preview-container');
    const uploadBtn = document.getElementById('upload-btn');
    if (!container) return;

    container.innerHTML = '';

    selectedFiles.forEach(file => {
        const div = document.createElement('div');
        div.className = 'staged-file';
        div.innerHTML = `
            <span>${file.name} (${formatFileSize(file.size)})</span>
            <span class="remove-file" onclick="removeStagedFile('${file.name}')">×</span>
        `;
        container.appendChild(div);
    });

    if (uploadBtn) {
        uploadBtn.disabled = selectedFiles.size === 0;
        uploadBtn.innerText = selectedFiles.size > 0 ? `Upload ${selectedFiles.size} File(s)` : 'Upload';
    }
}

function removeStagedFile(name) {
    selectedFiles.forEach(file => {
        if (file.name === name) selectedFiles.delete(file);
    });
    renderStagedFiles();
}

async function uploadStagedFiles() {
    if (selectedFiles.size === 0) return;

    const formData = new FormData();
    selectedFiles.forEach(file => {
        formData.append('files', file);
    });

    const btn = document.getElementById('upload-btn');
    if (btn) {
        btn.disabled = true;
        btn.innerText = 'Uploading...';
    }

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            showToast('Files uploaded successfully', 'success');
            selectedFiles.clear();
            renderStagedFiles();
            loadFiles();
            loadStats();
        } else {
            const err = await response.text();
            showToast('Upload failed', 'error');
            console.error(err);
        }
    } catch (error) {
        console.error('Upload Error:', error);
        showToast('Upload error', 'error');
    } finally {
        if (btn) {
            btn.disabled = selectedFiles.size === 0;
            btn.innerText = 'Upload';
        }
    }
}

async function loadFiles() {
    const list = document.getElementById('file-grid');
    if (!list) return;

    list.innerHTML = '<div class="skeleton" style="height: 50px;"></div>';

    try {
        const response = await fetch('/api/files');
        const data = await response.json();
        renderFiles(data.files || []);
    } catch (e) {
        console.error('Error loading files:', e);
        list.innerHTML = '<div class="empty-state">Failed to load files</div>';
    }
}

function renderFiles(files) {
    const list = document.getElementById('file-grid');
    if (!list) return;

    // Apply correct class for layout
    const isGrid = fileViewMode !== 'list';
    list.className = isGrid ? 'file-grid' : 'file-list';

    if (files.length === 0) {
        list.innerHTML = `<div class="empty-state"><p>No files uploaded</p></div>`;
        return;
    }

    window.allFiles = files; // Store globally for tag operations

    list.innerHTML = files.map(file => {
        const tagHtml = renderTags(file.name, file.tags || []);

        if (isGrid) {
            // GRID VIEW (Card)
            return `
            <div class="file-card" ondblclick="deleteFile('${file.name}')" title="${file.name}">
                <div class="file-icon">${getFileIcon(file.name)}</div>
                <div class="file-info">
                    <div class="file-name">${file.name}</div>
                    <div class="file-tags-container" style="display:flex; flex-wrap:wrap; gap:4px; margin-top:5px; justify-content:center;">
                        ${tagHtml}
                        <button class="add-tag-btn" onclick="promptAddTag('${file.name}')" style="background:none; border:1px dashed var(--text-muted); color:var(--text-muted); border-radius:10px; cursor:pointer; font-size:10px; padding:2px 6px;">+</button>
                    </div>
                    <div class="file-meta" style="margin-top:5px;">${formatFileSize(file.size)}</div>
                </div>
                 <button class="delete-btn-overlay" onclick="deleteFile('${file.name}')" title="Delete">×</button>
            </div>`;
        } else {
            // LIST VIEW (Row)
            // Name (30%) | Tags (30%) | Size (15%) | Date (15%) | Actions (10%)
            return `
            <div class="file-item" style="display:grid; grid-template-columns: 2fr 2fr 1fr 1.5fr 40px; align-items:center; padding:10px 15px; border-bottom:1px solid var(--border-color); gap:10px; width:100%;">
                
                <!-- Name & Icon (Left) -->
                <div style="display:flex; align-items:center; gap:12px; overflow:hidden; justify-content: flex-start;">
                    <div class="file-icon" style="font-size:1.4em; min-width: 24px; text-align:center;">${getFileIcon(file.name)}</div>
                    <div class="file-name" style="font-weight:600; font-size: 0.95em; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--text-color);">${file.name}</div>
                </div>

                <!-- Tags (Center) -->
                <div style="display:flex; flex-wrap:wrap; gap:5px; align-items:center;">
                    ${tagHtml}
                    <button onclick="promptAddTag('${file.name}')" style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:14px; opacity:0.5;">+</button>
                </div>

                <!-- Size -->
                 <div style="color:var(--text-color); font-size:0.9em; text-align:center;">${formatFileSize(file.size)}</div>

                <!-- Date (Right) -->
                <div style="color:var(--text-secondary); font-size:0.85em; text-align:right;">
                    ${file.modified || file.created || '-'}
                </div>

                <!-- Actions -->
                <div class="file-actions" style="text-align:right; display:flex; justify-content:flex-end;">
                     <button class="icon-btn delete-btn" onclick="deleteFile('${file.name}')" title="Delete" style="background:rgba(255,0,0,0.1); border:none; color:var(--danger-color); cursor:pointer; font-size: 1em; padding: 6px; border-radius: 4px; display:flex; align-items:center; justify-content:center; width: 30px; height: 30px;">
                        🗑️
                     </button>
                </div>
            </div>`;
        }
    }).join('');
}

function renderTags(filename, tags) {
    if (!tags || tags.length === 0) return '';
    return tags.map(tag => `
        <span class="file-tag" style="background:var(--accent-color); color:white; padding:2px 6px; border-radius:10px; font-size:10px; display:inline-flex; align-items:center; gap:3px;">
            ${tag}
            <span onclick="removeTag('${filename}', '${tag}')" style="cursor:pointer; opacity:0.7; font-weight:bold;">×</span>
        </span>
    `).join('');
}

async function promptAddTag(filename) {
    const tag = prompt("Enter tag name:");
    if (!tag) return;

    // Find file
    const file = window.allFiles.find(f => f.name === filename);
    if (!file) return;

    const currentTags = file.tags || [];
    if (currentTags.includes(tag)) return;

    const newTags = [...currentTags, tag];
    await updateFileTags(filename, newTags);
}

async function removeTag(filename, tag) {
    const file = window.allFiles.find(f => f.name === filename);
    if (!file) return;

    const newTags = (file.tags || []).filter(t => t !== tag);
    await updateFileTags(filename, newTags);
}

async function updateFileTags(filename, tags) {
    try {
        const response = await fetch(`/api/files/${filename}/tags`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tags })
        });
        if (response.ok) {
            loadFiles(); // Reload to refresh grid
        } else {
            showToast('Failed to update tags', 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Error updating tags', 'error');
    }
}

async function deleteFile(filename) {
    if (!confirm(`Delete ${filename}?`)) return;
    try {
        // Use encodeURIComponent to handle special characters in filenames
        const response = await fetch(`/api/files/${encodeURIComponent(filename)}`, { method: 'DELETE' });
        if (response.ok) {
            showToast('File deleted', 'success');
            loadFiles();
            loadStats();
        } else {
            const data = await response.json();
            showToast(data.error || 'Failed to delete file', 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Network error deleting file', 'error');
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function getFileIcon(filename) {
    return '📄';
}

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

// ==========================================
// PROMPT LIBRARY (Refactored v2.3)
// ==========================================
let allPrompts = []; // Store locally for client-side search

function openPromptLibrary() {
    const modal = document.getElementById('prompt-library-modal');
    if (!modal) return;
    modal.style.display = 'flex';
    loadPrompts();
    showPromptList(); // Ensure list view is default
}

function closePromptLibrary() {
    const modal = document.getElementById('prompt-library-modal');
    if (modal) modal.style.display = 'none';
}

function showCreatePromptForm() {
    const listView = document.getElementById('prompt-list-view');
    const formView = document.getElementById('prompt-form-view');
    if (listView) listView.style.display = 'none';
    if (formView) formView.style.display = 'block';
    // Clear inputs
    const titleInput = document.getElementById('prompt-title-input');
    const contentInput = document.getElementById('prompt-content-input');
    if (titleInput) titleInput.value = '';
    if (contentInput) contentInput.value = '';
}

function showPromptList() {
    const formView = document.getElementById('prompt-form-view');
    const listView = document.getElementById('prompt-list-view');
    if (formView) formView.style.display = 'none';
    if (listView) listView.style.display = 'block';
}

async function loadPrompts() {
    const container = document.getElementById('prompts-container');
    container.innerHTML = '<div style="text-align:center; padding:20px; color:var(--text-muted);">Loading...</div>';

    try {
        const res = await fetch('/api/prompts');
        allPrompts = await res.json();
        renderPrompts(allPrompts);
    } catch (e) {
        container.innerHTML = '<div style="color:var(--error-color); padding:20px; text-align:center;">Error loading prompts.</div>';
        showToast('Failed to load prompts', 'error');
    }
}

function renderPrompts(prompts) {
    const container = document.getElementById('prompts-container');
    container.innerHTML = '';

    if (prompts.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 40px 20px; color: var(--text-muted);">
                <div style="font-size: 2em; margin-bottom: 10px;">📝</div>
                <div>No saved prompts found.</div>
                <div style="font-size: 0.9em; margin-top: 5px;">Create one to get started!</div>
            </div>`;
        return;
    }

    prompts.forEach(p => {
        const card = document.createElement('div');
        card.style.cssText = 'padding:15px; border-bottom:1px solid var(--border-color); transition:background 0.2s;';
        card.onmouseenter = () => card.style.background = 'rgba(255,255,255,0.03)';
        card.onmouseleave = () => card.style.background = 'transparent';

        // Store content in dataset to avoid escaping issues
        card.dataset.promptContent = p.content;
        card.dataset.promptId = p.id;

        card.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <div style="font-weight:600; color:var(--text-color); font-size:1em;">${escapeHtml(p.title)}</div>
                <button class="delete-prompt-btn" title="Delete Prompt" 
                    style="color:var(--text-muted); background:none; border:none; cursor:pointer; padding:4px; font-size:1em; opacity:0.6; transition:opacity 0.2s;"
                    onmouseenter="this.style.opacity=1" onmouseleave="this.style.opacity=0.6">
                    🗑️
                </button>
            </div>
            <div style="font-size:0.85em; color:var(--text-secondary); max-height:50px; overflow:hidden; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; margin-bottom:10px;">
                ${escapeHtml(p.content)}
            </div>
            <button class="use-prompt-btn primary-btn" style="width:100%; padding:8px; font-size:0.9em; border-radius:6px;">
                ✨ Use This Prompt
            </button>
        `;

        // Attach event listeners safely
        card.querySelector('.delete-prompt-btn').addEventListener('click', () => deletePrompt(p.id));
        card.querySelector('.use-prompt-btn').addEventListener('click', () => usePrompt(p.content));

        container.appendChild(card);
    });
}

function filterPrompts() {
    const query = document.getElementById('prompt-search').value.toLowerCase();
    const filtered = allPrompts.filter(p =>
        p.title.toLowerCase().includes(query) ||
        p.content.toLowerCase().includes(query)
    );
    renderPrompts(filtered);
}

async function savePrompt() {
    const title = document.getElementById('prompt-title-input').value.trim();
    const content = document.getElementById('prompt-content-input').value.trim();

    if (!title || !content) {
        showToast('Title and content are required', 'warning');
        return;
    }

    try {
        const res = await fetch('/api/prompts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, content })
        });

        if (res.ok) {
            showToast('Prompt saved!', 'success');
            showPromptList();
            loadPrompts(); // Reload list
        } else {
            showToast('Failed to save prompt', 'error');
        }
    } catch (e) {
        showToast('Error saving prompt', 'error');
    }
}

async function deletePrompt(id) {
    if (!confirm('Are you sure you want to delete this prompt?')) return;

    try {
        const res = await fetch(`/api/prompts/${id}`, { method: 'DELETE' });
        if (res.ok) {
            showToast('Prompt deleted', 'success');
            loadPrompts();
        } else {
            showToast('Failed to delete prompt', 'error');
        }
    } catch (e) {
        showToast('Error deleting prompt', 'error');
    }
}

function usePrompt(content) {
    // Update the system prompt textarea
    const systemPrompt = document.getElementById('system-prompt');
    if (systemPrompt) {
        systemPrompt.value = content;
    }

    // Close the modal
    closePromptLibrary();

    // Navigate to chat view
    showView('chat');

    // Paste content into the chat message input
    const messageInput = document.getElementById('chat-input');
    if (messageInput) {
        messageInput.value = content;
        messageInput.focus();
    }

    showToast('Prompt loaded! Ready to send.', 'success');
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


function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    // Get notification duration from setting (in seconds), default to 3
    let durationSeconds = 3;
    const durationInput = document.getElementById('notification-duration');
    if (durationInput && durationInput.value) {
        durationSeconds = parseInt(durationInput.value) || 3;
    }
    const durationMs = durationSeconds * 1000;

    // Desktop Notification Trigger
    const desktopEnabled = document.getElementById('desktop-notifications')?.checked;
    if (desktopEnabled && 'Notification' in window && Notification.permission === 'granted') {
        try {
            const n = new Notification('Onyx', { body: message });
            // Auto-close after duration
            setTimeout(() => n.close(), durationMs);
        } catch (e) { console.error('Notification error', e); }
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    let icon = type === 'error' ? '❌' : type === 'success' ? '✅' : type === 'warning' ? '⚠️' : 'ℹ️';
    toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.5s ease-out forwards';
        setTimeout(() => toast.remove(), 500);
    }, durationMs);
}

// Override default alert
window.alert = function (msg) { showToast(msg, 'warning'); };

// ============== CONTEXT MENU ==============
function showContextMenu(event, type, id) {
    event.preventDefault();
    event.stopPropagation();
    const menu = document.getElementById('context-menu');

    // Store the target filename/id for event handlers
    menu.dataset.targetId = id;
    menu.dataset.targetType = type;

    let items = '';
    if (type === 'indexed') {
        items = `
            <div class="context-menu-item" data-action="preview">
                <img src="https://img.icons8.com/ios/20/ffffff/file-preview.png" alt="Preview" style="width:16px;height:16px;vertical-align:middle;margin-right:6px;"> Preview
            </div>

            <div class="context-menu-item danger" data-action="delete">
                <img src="https://img.icons8.com/color/20/filled-trash.png" alt="Delete" style="width:16px;height:16px;vertical-align:middle;margin-right:6px;"> Remove
            </div>

        `;

    }
    menu.innerHTML = items;

    // Add event delegation for menu items
    const menuItems = menu.querySelectorAll('.context-menu-item');
    menuItems.forEach(item => {
        item.addEventListener('click', function (e) {
            e.stopPropagation();
            const action = this.dataset.action;
            const targetId = menu.dataset.targetId;

            console.log('Context menu action:', action, 'Target ID:', targetId);

            if (action === 'delete') {
                deleteFile(targetId);
            } else if (action === 'preview') {
                showPreview(targetId);
            }

            // Close menu after action
            menu.classList.remove('visible');
            menu.style.display = 'none';
        });
    });

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
function showSessionContextMenu(event, sessionId, sessionName, isPinned) {
    event.preventDefault();
    event.stopPropagation();

    const menu = document.getElementById('context-menu');
    const pinText = isPinned ? 'Unpin' : 'Pin';
    // Use simple text markers instead of emojis to avoid encoding issues
    const pinIcon = isPinned ? '<span style="color:var(--accent-color)">[x]</span>' : '<span>[ ]</span>';

    menu.innerHTML = `
        <div class="context-menu-item" onclick="toggleSessionPin(${sessionId}, ${isPinned || 0}); document.getElementById('context-menu').classList.remove('visible');">
            ${pinIcon} ${pinText} Session
        </div>
        <div class="context-menu-item" onclick="openRenameModal(${sessionId}, '${sessionName}'); document.getElementById('context-menu').classList.remove('visible');">
            [R] Rename
        </div>
        <div class="context-menu-item" onclick="exportSession(${sessionId}, '${sessionName}', 'txt')">
            [TXT] Export as TXT
        </div>
        <div class="context-menu-item" onclick="exportSession(${sessionId}, '${sessionName}', 'md')">
            [MD] Export as Markdown
        </div>
        <div class="context-menu-divider"></div>
        <div class="context-menu-item danger" onclick="deleteSession(${sessionId}, event)">
            [Del] Delete
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
    // Global Header Elements
    const dot = document.getElementById('status-dot');
    const text = document.getElementById('status-text');

    // Control Panel Elements
    const ctrlDot = document.getElementById('ollama-ctrl-dot');
    const ctrlText = document.getElementById('ollama-ctrl-text');
    const btnStart = document.getElementById('btn-ollama-start');
    const btnRestart = document.getElementById('btn-ollama-restart');

    // console.log("checkHealth running...");

    // Set Loading State ONLY if not already checking (to avoid flicker)
    // Actually, setting loading state on every poll might be annoying.
    // Let's only set loading if verification takes > 500ms? No, stick to simple for now.
    // To mimic "Connected" feeling, we don't always flash 'Checking...' in the UI unless it's a manual refresh.
    // But since this function is also called by polling, we should be subtle.
    // Recommendation: Don't change text to "Checking..." for polling, only for manual or initial.
    // For now, let's just update the status effectively.

    try {
        const response = await fetch('/api/health');
        const data = await response.json();

        let isConnected = false;
        let isBackendUp = false;

        if (data.ollama && data.ollama.available) {
            isConnected = true;
            if (dot) dot.title = `Model: ${data.ollama.model || 'Unknown'}`;
        } else if (data.status === 'online' || response.ok) {
            isBackendUp = true;
            if (dot) dot.title = "Backend is online, but no model responding";
        }

        // --- UPDATE UI STATE ---
        const statusClass = isConnected ? 'status-dot' : (isBackendUp ? 'status-dot loading' : 'status-dot offline');
        // Note: 'loading' is yellow/orange, good for "Backend Up but No Logic", 'offline' is red.
        const statusMsg = isConnected ? 'Connected' : (isBackendUp ? 'Backend Ready' : 'Offline');

        // Update Global Header
        if (dot) dot.className = statusClass;
        if (text) text.innerText = statusMsg;

        // Update Control Panel
        if (ctrlDot) ctrlDot.className = statusClass;
        if (ctrlText) ctrlText.innerText = statusMsg;

        // Update Unified Status Bar (System Status)
        const unifiedStatus = document.getElementById('ollama-status');
        if (unifiedStatus) {
            unifiedStatus.innerText = statusMsg;
            unifiedStatus.style.color = isConnected ? 'var(--success-color)' : (isBackendUp ? 'var(--warning-color)' : 'var(--error-color)');
        }

        // Update Buttons
        if (btnStart) {
            if (isConnected) {
                // RUNNING
                btnStart.disabled = true;
                btnStart.style.opacity = '0.5';
                btnStart.style.cursor = 'not-allowed';
                btnStart.innerHTML = '<span>✔</span> Running';
            } else {
                // STOPPED
                btnStart.disabled = false;
                btnStart.style.opacity = '1';
                btnStart.style.cursor = 'pointer';
                btnStart.innerHTML = '<span>▶</span> Start';
            }
        }

        // Ensure Restart is always enabled (unless we are performing an action, handled by controlOllama)
        // But if restart is currently running, controlOllama handles the disables. 
        // We shouldn't re-enable it if it was disabled by controlOllama?
        // Actually controlOllama disables it, then awaits logic, then runs checkHealth.
        // So checkHealth effectively re-evaluates state.

    } catch (e) {
        console.error("Health Check Error:", e);
        if (dot) dot.className = 'status-dot offline';
        if (text) text.innerText = 'Error';
        if (ctrlDot) ctrlDot.className = 'status-dot offline';
        if (ctrlText) ctrlText.innerText = 'Connection Error';

        const unifiedStatus = document.getElementById('ollama-status');
        if (unifiedStatus) {
            unifiedStatus.innerText = 'Error';
            unifiedStatus.style.color = 'var(--error-color)';
        }

        // If error, enable start button potentially? Or disable everything?
        // Safest: Enable start in case it's just down.
        if (btnStart) {
            btnStart.disabled = false;
            btnStart.style.opacity = '1';
            btnStart.style.cursor = 'pointer';
            btnStart.innerText = '▶ Start';
        }
    }
}

async function controlOllama(action) {
    const btn = document.getElementById(`btn-ollama-${action}`);
    const originalText = btn ? btn.innerText : '';
    if (btn) {
        btn.disabled = true;
        btn.innerText = '⏳ ...';
    }

    showToast(`Attempting to ${action} Ollama...`, 'info');

    try {
        const response = await fetch('/api/system/ollama/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: action })
        });
        const data = await response.json();

        if (data.status === 'success') {
            showToast(data.message, 'success');
            // Poll for health update after delay
            setTimeout(checkHealth, 2000);
            setTimeout(checkHealth, 5000);
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (e) {
        showToast('Network error: ' + e.message, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerText = originalText;
            checkHealth(); // Re-check status immediately to update UI state
        }
    }
}

function toggleMode() {
    const checkbox = document.getElementById('mode-toggle-checkbox');
    const status = document.getElementById('mode-status');

    // Determine mode based on checkbox state
    // Checked = CLI mode, Unchecked = Browser mode
    if (checkbox && checkbox.checked) {
        currentMode = 'cli';
        if (status) status.innerHTML = 'Mode: <strong>CLI Chat</strong>';
        showView('controls');
    } else {
        currentMode = 'browser';
        if (status) status.innerHTML = 'Mode: <strong>Browser Chat</strong>';
        showView('chat');
    }

    fetch('/set_mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: currentMode })
    }).catch(console.error);
}

// ============== CHAT & SESSION MANAGEMENT ==============
// ============== CHAT & SESSION MANAGEMENT ==============

// Bulk Delete State
let isBulkDeleteMode = false;
let selectedSessions = new Set();

function handleBulkDeleteClick(event) {
    if (event) event.preventDefault();
    console.log('[App] handleBulkDeleteClick called. Mode:', isBulkDeleteMode);
    if (isBulkDeleteMode) {
        console.log('[App] Triggering deleteSelectedChats');
        deleteSelectedChats();
    } else {
        console.log('[App] Toggling bulk delete mode');
        toggleBulkDeleteMode();
    }
}

function toggleBulkDeleteMode() {
    isBulkDeleteMode = !isBulkDeleteMode;
    selectedSessions.clear();

    const btn = document.getElementById('bulk-delete-toggle-btn');
    const selectContainer = document.getElementById('bulk-select-container');
    const selectAllCheckbox = document.getElementById('select-all-checkbox');

    if (isBulkDeleteMode) {
        btn.textContent = 'Delete (0)';
        btn.classList.add('danger-btn');
        // Action handled by handleBulkDeleteClick
        selectContainer.style.display = 'block';
        if (selectAllCheckbox) selectAllCheckbox.checked = false;
    } else {
        btn.textContent = 'Clear chats';
        btn.classList.remove('danger-btn');
        // Action handled by handleBulkDeleteClick
        selectContainer.style.display = 'none';
        selectedSessions.clear();
    }

    loadSessions();
}

function updateBulkDeleteButton() {
    const btn = document.getElementById('bulk-delete-toggle-btn');
    if (isBulkDeleteMode && btn) {
        const count = selectedSessions.size;
        btn.textContent = `Delete (${count})`;
    }
}

function toggleSelectAll(checked) {
    const checkboxes = document.querySelectorAll('.session-checkbox');
    checkboxes.forEach(cb => {
        cb.checked = checked;
        const id = parseInt(cb.dataset.id);
        if (checked) {
            selectedSessions.add(id);
        } else {
            selectedSessions.delete(id);
        }
    });
    updateBulkDeleteButton();
}

function toggleSessionSelection(id, event) {
    if (event) event.stopPropagation();
    const checkbox = document.querySelector(`.session-checkbox[data-id="${id}"]`);
    const sessionId = parseInt(id);

    if (checkbox) {
        if (checkbox.checked) {
            selectedSessions.add(sessionId);
        } else {
            selectedSessions.delete(sessionId);
            // Uncheck select all if one is unchecked
            document.getElementById('select-all-checkbox').checked = false;
        }
        updateBulkDeleteButton();
    }
}

async function deleteSelectedChats() {
    if (selectedSessions.size === 0) {
        toggleBulkDeleteMode();
        return;
    }

    // Show custom modal instead of native confirm
    const modal = document.getElementById('confirm-modal');
    const msg = document.getElementById('confirm-modal-message');
    const okBtn = document.getElementById('confirm-modal-ok');

    if (modal && msg && okBtn) {
        msg.textContent = `Are you sure you want to delete ${selectedSessions.size} chats? This cannot be undone.`;

        // Remove existing listeners to prevent duplicates/wrong actions
        const newOkBtn = okBtn.cloneNode(true);
        okBtn.parentNode.replaceChild(newOkBtn, okBtn);

        newOkBtn.onclick = executeBulkDelete;

        // Also handle cancel button cleanup if needed, but hideConfirmModal is static

        modal.style.display = 'flex';
    } else {
        console.error('Confirm modal elements missing');
        // Fallback to native if modal broken
        if (confirm(`Are you sure you want to delete ${selectedSessions.size} chats?`)) {
            executeBulkDelete();
        }
    }
}

async function executeBulkDelete() {
    hideConfirmModal();

    console.log('[BulkDelete] About to show toast...');
    showToast('Deleting chats...', 'info');

    // DEBUG: Log the sessions to be deleted
    console.log('[BulkDelete] Starting delete for sessions:', Array.from(selectedSessions));

    try {
        const payload = { session_ids: Array.from(selectedSessions) };
        console.log('[BulkDelete] Payload:', payload);

        const response = await fetch('/api/sessions/bulk_delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        console.log('[BulkDelete] Response status:', response.status);

        const data = await response.json();

        if (data.status === 'success') {
            showToast(`Deleted ${data.deleted_count} chats`, 'success');

            isBulkDeleteMode = false;

            // Reset button UI
            const btn = document.getElementById('bulk-delete-toggle-btn');
            if (btn) {
                btn.textContent = 'Clear chats';
                btn.classList.remove('danger-btn');
            }
            document.getElementById('bulk-select-container').style.display = 'none';
            selectedSessions.clear();

            // Reload EVERYTHING
            if (data.deleted_count > 0) {
                currentSessionId = null;
                await loadSessions();
                loadChatHistory();
            } else {
                await loadSessions();
            }
        } else {
            showToast('Failed to delete chats: ' + data.error, 'error');
        }
    } catch (e) {
        console.error('[BulkDelete] Error:', e);
        showToast('Error deleting chats', 'error');
    }
}


async function toggleSessionPin(sessionId, currentStatus, event) {
    if (event) event.stopPropagation();

    try {
        const response = await fetch(`/api/sessions/${sessionId}/pin`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_pinned: !currentStatus })
        });
        const data = await response.json();
        if (data.status === 'success') {
            loadSessions(); // Reload list
        } else {
            console.error('Failed to toggle pin');
            showToast('Failed to toggle pin', 'error');
        }
    } catch (e) {
        console.error('Error toggling pin:', e);
        showToast('Error toggling pin', 'error');
    }
}


/**
 * Export a chat session as Markdown file
 */
async function exportSession(sessionId, event) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }

    try {
        showToast('Exporting chat...', 'info');

        // Use Markdown format for better readability
        const url = `/api/sessions/${sessionId}/export?format=md`;

        // Create a temporary link to trigger download
        const link = document.createElement('a');
        link.href = url;
        link.download = `chat_${sessionId}.md`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        showToast('Chat exported successfully!', 'success');
    } catch (e) {
        console.error('Error exporting session:', e);
        showToast('Failed to export chat', 'error');
    }
}


async function loadSessions() {
    try {
        const response = await fetch('/api/sessions');
        const data = await response.json();
        const sessions = data.sessions || [];
        const list = document.getElementById('session-list');
        if (!list) return;

        // Auto-selection removed: Do not defaults to data.current
        // if (!currentSessionId && data.current) {
        //     currentSessionId = data.current;
        // }

        list.innerHTML = sessions.map(session => {
            const isSelected = selectedSessions.has(session.id);

            let actionHtml = '';
            let selectionHtml = '';

            if (isBulkDeleteMode) {
                selectionHtml = `
                    <div style="margin-right: 10px;" onclick="event.stopPropagation()">
                        <input type="checkbox" class="session-checkbox" data-id="${session.id}" 
                               onchange="toggleSessionSelection(${session.id}, event)" 
                               ${isSelected ? 'checked' : ''} 
                               style="transform: scale(1.2); cursor: pointer;">
                    </div>
                `;
            } else {
                const isPinned = session.is_pinned;
                const pinColor = isPinned ? '#f1c40f' : 'var(--text-muted)';
                const pinTitle = isPinned ? 'Unpin Session' : 'Pin Session';

                actionHtml = `
                    <button class="action-btn" onclick="toggleSessionPin(${session.id}, ${isPinned || 0}, event)" title="${pinTitle}">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="${isPinned ? pinColor : 'none'}" stroke="${pinColor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <line x1="12" y1="17" x2="12" y2="22"></line>
                            <path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V17z"></path>
                        </svg>
                    </button>
                    <button class="action-btn" onclick="openRenameModal(${session.id}, '${escapeHtml(session.name)}', event)" title="Rename Chat">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                           <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                           <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                        </svg>
                    </button>
                    <button class="action-btn export-btn" onclick="exportSession(${session.id}, event)" title="Export Chat">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                    </button>
                    <button class="delete-session-btn" onclick="deleteSession(${session.id}, event)" title="Delete Session">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="#e74c3c">
                            <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM8 9h8v10H8V9zm7.5-5l-1-1h-5l-1 1H5v2h14V4h-3.5z"/>
                            <path d="M9 12h2v5H9zm4 0h2v5h-2z" fill="white"/>
                        </svg>
                    </button>
                `;
            }

            return `
            <div class="history-item ${session.id === currentSessionId ? 'active' : ''}" 
                 onclick="switchSession(${session.id})"
                oncontextmenu="showSessionContextMenu(event, ${session.id}, '${escapeHtml(session.name)}', ${session.is_pinned || 0})"
                 title="${escapeHtml(session.name)}" style="display: flex; align-items: center;">
                ${selectionHtml}
                <span class="history-name" style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(session.name)}</span>
                ${actionHtml}
            </div>
        `}).join('');

        // Update select all checkbox if needed
        if (isBulkDeleteMode) {
            const selectAllCheckbox = document.getElementById('select-all-checkbox');
            if (selectAllCheckbox) {
                const allSelected = sessions.length > 0 && sessions.every(s => selectedSessions.has(s.id));
                selectAllCheckbox.checked = allSelected;
            }
        }
    } catch (e) {
        console.error('Failed to load sessions:', e);
        showToast('Failed to load sessions', 'error');
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
    if (typeof toggleEmptyState === 'function') {
        toggleEmptyState(true);
    } else {
        const emptyState = document.getElementById('chat-empty-state');
        if (emptyState) emptyState.style.display = 'flex';
    }

    // Update sidebar to show no active session
    document.querySelectorAll('.history-item').forEach(item => {
        item.classList.remove('active');
    });

    showView('chat');
    // Ensure no modals are trapping focus
    hideConfirmModal();
    closeRenameModal();
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
            // track last ID
            const lastMsg = data.messages[data.messages.length - 1];
            if (lastMsg && lastMsg.id) lastMessageId = lastMsg.id;

            historyContainer.innerHTML = data.messages.map(msg => `
                <div class="chat-message ${msg.role}-message">
                    <div class="message-content">${msg.role === 'assistant' ? (typeof marked !== 'undefined' ? marked.parse(msg.content) : msg.content) : msg.content}</div>
                    <div class="message-meta">${new Date(msg.created_at).toLocaleTimeString()}</div>
                </div>
            `).join('');
        } else {
            toggleEmptyState(true);
            historyContainer.innerHTML = '';
            lastMessageId = 0;
        }
        // Re-add scroll anchor after innerHTML replacement
        ensureScrollAnchor();
        // Scroll to bottom after content loads
        setTimeout(() => scrollToBottom(), 100);

    } catch (e) {
        console.error('loadChatHistory error:', e);
        historyContainer.innerHTML = '<div class="error-message">Failed to load history</div>';
    }
}

// ============== REAL-TIME SYNC ==============
async function pollChatMessages() {
    if (!currentSessionId || currentMode !== 'browser') return;

    try {
        const url = `/api/sessions/${currentSessionId}?after_id=${lastMessageId}`;
        const response = await fetch(url);
        if (!response.ok) return;

        const data = await response.json();
        if (data.messages && data.messages.length > 0) {
            const historyContainer = document.getElementById('chat-history');
            if (historyContainer) {
                // Remove empty state if present
                const emptyState = document.getElementById('chat-empty-state');
                if (emptyState && emptyState.style.display !== 'none') {
                    toggleEmptyState(false);
                }

                data.messages.forEach(msg => {
                    // Update last ID
                    if (msg.id > lastMessageId) lastMessageId = msg.id;

                    // Append Message
                    const div = document.createElement('div');
                    div.className = `chat-message ${msg.role}-message`;
                    div.innerHTML = `
                        <div class="message-content">${msg.role === 'assistant' ? (typeof marked !== 'undefined' ? marked.parse(msg.content) : msg.content) : msg.content}</div>
                        <div class="message-meta">${new Date(msg.created_at).toLocaleTimeString()}</div>
                    `;
                    historyContainer.appendChild(div);
                });
                scrollToBottom();
            }
        }
    } catch (e) {
        // Silent fail for polling
    }
}


async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    const images = (typeof currentFiles !== 'undefined' && currentFiles) ? currentFiles.filter(f => f.type === 'image') : [];
    const docs = (typeof currentFiles !== 'undefined' && currentFiles) ? currentFiles.filter(f => f.type === 'document') : [];
    const hasFiles = images.length > 0 || docs.length > 0;

    if (!message && !hasFiles) return;
    if (isGenerating) return; // Prevent double-submit

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
                // Don't call loadSessions() here - it will be called at the end
                // This prevents potential duplicate loading
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

    // Add user message visually with attachments
    let userMsgHTML = `<div class="chat-message user-message">`;
    userMsgHTML += `<div class="message-content">${escapeHtml(message)}</div>`;

    // Render attachments inline if present
    if (hasFiles) {
        if (images.length > 0) {
            userMsgHTML += `<div class="message-attachments">`;
            for (const img of images) {
                userMsgHTML += `<img src="${img.data}" title="${escapeHtml(img.name)}" style="max-width: 200px; max-height: 200px; border-radius: 8px; margin: 4px; object-fit: cover;">`;
            }
            userMsgHTML += `</div>`;
        }
        if (docs.length > 0) {
            userMsgHTML += `<div class="message-attachments">`;
            for (const doc of docs) {
                const ext = doc.name.split('.').pop().toUpperCase();
                userMsgHTML += `<div class="doc-chip" style="display: inline-flex; align-items: center; padding: 8px 12px; background: var(--bg-dark); border-radius: 6px; margin: 4px; font-size: 0.85em;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 6px;"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M12 18v-6"/><path d="m9 15 3 3 3-3"/></svg>
                    ${escapeHtml(doc.name)}
                </div>`;
            }
            userMsgHTML += `</div>`;
        }
    }

    userMsgHTML += `</div>`;
    historyContainer.innerHTML += userMsgHTML;


    // Add bot message container
    const botMsgDiv = document.createElement('div');
    botMsgDiv.className = 'chat-message bot-message';
    botMsgDiv.innerHTML = '<div class="message-content"><span class="loading-spinner"></span> Thinking...</div>';
    historyContainer.appendChild(botMsgDiv);

    // Ensure anchor exists and scroll to bottom
    ensureScrollAnchor();
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

        // Build payload with files
        const payload = {
            message: message,
            session_id: currentSessionId,
            files: (typeof currentFiles !== 'undefined' && currentFiles) ? currentFiles : [],
            deep_search: typeof isDeepSearchEnabled !== 'undefined' ? isDeepSearchEnabled : false
        };

        // Clear attachments immediately
        if (typeof currentFiles !== 'undefined') {
            currentFiles = [];
            if (typeof renderFilePreviews === 'function') renderFilePreviews();
        }

        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
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

            // Check for Approval Request Token
            if (fullText.includes('[APPROVAL_REQUIRED]')) {
                const parts = fullText.split('[APPROVAL_REQUIRED]');
                // The part before token is normal text (if any)
                const preText = parts[0];
                const jsonStr = parts[1].trim();

                // Render prefix info if any
                if (preText) {
                    contentDiv.innerHTML = typeof marked !== 'undefined' ? marked.parse(preText) : escapeHtml(preText);
                }

                try {
                    const approvalData = JSON.parse(jsonStr);
                    renderApprovalCard(contentDiv, approvalData, preText);
                    // Stop processing stream as backend has paused
                    break;
                } catch (e) {
                    console.error("Failed to parse approval data", e);
                }
            } else {
                // Normal stream
                contentDiv.innerHTML = typeof marked !== 'undefined' ? marked.parse(fullText) : escapeHtml(fullText);
            }

            // Scroll current message into view
            botMsgDiv.scrollIntoView({ behavior: "smooth", block: "end" });
        }

        const endTime = performance.now();
        const duration = ((endTime - startTime) / 1000).toFixed(1);

        // Add metrics footer (only if not waiting for approval)
        if (!fullText.includes('[APPROVAL_REQUIRED]')) {
            let metricsHtml = `<div class="message-meta">${duration}s`;
            metricsHtml += ` • AI</div>`;
            botMsgDiv.insertAdjacentHTML('beforeend', metricsHtml);
        }

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
    // Use the anchor element for reliable scrollIntoView
    const anchor = document.getElementById('chat-scroll-anchor');
    if (anchor) {
        anchor.scrollIntoView({ behavior: 'smooth', block: 'end' });
        return;
    }

    // Fallback: manual scroll
    const history = document.getElementById('chat-history');
    if (history) {
        history.scrollTop = history.scrollHeight;
    }
}

// Ensure anchor exists in chat-history (re-add if content replaced)
function ensureScrollAnchor() {
    const history = document.getElementById('chat-history');
    if (!history) return;

    let anchor = document.getElementById('chat-scroll-anchor');
    if (!anchor) {
        anchor = document.createElement('div');
        anchor.id = 'chat-scroll-anchor';
        anchor.style.height = '1px';
        history.appendChild(anchor);
    }
}


// ============== INDEX MANAGEMENT ==============
// ============== INDEX MANAGEMENT ==============
async function clearIndex(btn) {
    // 1. Check if button is already in "confirm" state
    if (!btn.dataset.confirming) {
        // First Click: Switch to Confirm State
        btn.dataset.confirming = "true";
        btn.dataset.originalText = btn.innerHTML;
        btn.innerHTML = "⚠️ Click Again to Confirm";
        btn.style.backgroundColor = "#ff3b30"; // Bright red
        btn.style.transform = "scale(1.05)";

        // Auto-reset after 3 seconds if not clicked
        setTimeout(() => {
            if (btn.dataset.confirming) {
                delete btn.dataset.confirming;
                btn.innerHTML = btn.dataset.originalText;
                btn.style.backgroundColor = "";
                btn.style.transform = "";
            }
        }, 3000);
        return;
    }

    // 2. Confirmed Action
    delete btn.dataset.confirming;
    btn.innerHTML = "Clearing...";
    btn.disabled = true;

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
    } finally {
        // Restore button state
        btn.innerHTML = btn.dataset.originalText;
        btn.disabled = false;
        btn.style.backgroundColor = "";
        btn.style.transform = "";
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

// ============== KNOWLEDGE GRAPH PLACEHOLDER ==============
function initGraphPlaceholder() {
    // Placeholder for future knowledge graph visualization
    const graphContainer = document.getElementById('knowledge-graph');
    if (graphContainer) {
        graphContainer.innerHTML = '<div style="display:flex;justify-content:center;align-items:center;height:100%;color:#888;font-size:0.9em;">Knowledge Graph visualization coming soon</div>';
    }
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
    loadFiles();
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

    // Global click listener to close context menu
    document.addEventListener('click', function (e) {
        const menu = document.getElementById('context-menu');
        if (menu && menu.classList.contains('visible') && !menu.contains(e.target)) {
            menu.classList.remove('visible');
            menu.style.display = 'none';
        }
    });

    // Global right-click listener to close context menu if clicking elsewhere
    document.addEventListener('contextmenu', function (e) {
        const menu = document.getElementById('context-menu');
        if (menu && menu.classList.contains('visible') && !menu.contains(e.target)) {
            // If clicking on a history item, let showSessionContextMenu handle it (don't hide immediately)
            if (!e.target.closest('.history-item')) {
                menu.classList.remove('visible');
                menu.style.display = 'none';
            }
        }
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

        // 2. Sync Button State (Fixes persistence/reload issue)
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.mode === config.mode) {
                btn.classList.add('active');
            }
        });

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
                // Browser Mode
                inputBar.classList.remove('disabled');
                inputBar.style.opacity = '1';
                inputBar.style.pointerEvents = 'auto';
                const overlay = document.getElementById('cli-overlay');
                if (overlay) overlay.remove();

                // Poll for new messages (Real-time Sync)
                pollChatMessages();
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

// ============== PAGE INITIALIZATION ==============
document.addEventListener('DOMContentLoaded', async function () {
    // Initialize App Components
    await checkHealth();
    await loadSettings();
    await loadSessions();
    loadStats();

    // Restore theme
    const savedTheme = localStorage.getItem('theme') || 'dark';
    if (savedTheme === 'light') {
        document.body.classList.remove('dark-theme');
    } else {
        document.body.classList.add('dark-theme');
    }
    updateThemeIcon(savedTheme === 'dark');

    // Ensure anchor exists and scroll to bottom on load
    setTimeout(() => {
        ensureScrollAnchor();
        scrollToBottom();
    }, 500);
});

// Also scroll when switching to chat view
// (Moved logic to DOMContentLoaded)

// ==========================================
// AGENTIC UI HANDLERS (Phase 1.2)
// ==========================================

function renderApprovalCard(container, data, preText) {
    // data = { tool, args, id, reason }
    const cardId = `approval-${data.id}`;

    // Create card HTML with approval/deny buttons
    // We use onclick to call global handlers
    const cardHtml = `
    <div id="${cardId}" class="approval-card" style="margin-top: 10px; border: 1px solid #e74c3c; background: rgba(231, 76, 60, 0.1); border-radius: 8px; padding: 15px;">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px; color: #e74c3c; font-weight: bold;">
            <span style="font-size: 1.2em;">⚠️</span> Approval Required
        </div>
        <div style="margin-bottom: 15px;">
            <div style="font-weight: 600; margin-bottom: 5px;">Action: <code style="color: #e74c3c; background: #333; padding: 2px 5px; border-radius: 3px;">${data.tool}</code></div>
            <div style="font-size: 0.9em; color: var(--text-muted); font-family: monospace; white-space: pre-wrap;">Arguments: ${JSON.stringify(data.args, null, 2)}</div>
            <div style="margin-top: 5px; font-style: italic; font-size: 0.9em; background: rgba(0,0,0,0.2); padding: 5px; border-left: 3px solid #e74c3c;">Reason: ${data.reason}</div>
        </div>
        <div class="approval-actions" style="display: flex; gap: 10px;">
            <button onclick="approveAction('${data.id}', '${cardId}')" class="primary-btn" style="background: #27ae60; flex: 1; justify-content: center;">✅ Approve</button>
            <button onclick="denyAction('${data.id}', '${cardId}')" class="primary-btn" style="background: #e74c3c; flex: 1; justify-content: center;">❌ Deny</button>
        </div>
    </div>
    `;

    // Append to existing text (careful not to overwrite if streaming was midway, but we broke stream)
    // We assume container has the preCheck text logic already handled in caller
    container.insertAdjacentHTML('beforeend', cardHtml);
}

async function approveAction(actionId, cardId) {
    handleActionDecision(actionId, cardId, 'approve');
}

async function denyAction(actionId, cardId) {
    handleActionDecision(actionId, cardId, 'deny');
}

async function handleActionDecision(actionId, cardId, decision) {
    const card = document.getElementById(cardId);
    if (!card) return;

    // Disable buttons
    const buttons = card.querySelectorAll('button');
    buttons.forEach(btn => btn.disabled = true);

    // Show spinner
    const statusDiv = document.createElement('div');
    statusDiv.style.marginTop = '10px';
    statusDiv.style.textAlign = 'center';
    statusDiv.style.fontStyle = 'italic';
    statusDiv.innerHTML = decision === 'approve' ? '<span class="loading-spinner"></span> Executing...' : 'Cancelling...';
    card.appendChild(statusDiv);

    try {
        const response = await fetch('/api/agent/allow', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentSessionId,
                action_id: actionId,
                decision: decision
            })
        });

        const data = await response.json();

        if (data.status === 'success') {
            // Update Card to Success State
            card.style.borderColor = '#27ae60';
            card.style.background = 'rgba(39, 174, 96, 0.1)';
            card.innerHTML = `
                <div style="color: #27ae60; font-weight: bold; display: flex; align-items: center; gap: 8px;">
                    <span>✅</span> Action Approved & Executed
                </div>
                <div style="margin-top: 10px; font-size: 0.9em;">
                    <strong>Result:</strong>
                    <pre style="background: #111; color: #eee; padding: 10px; margin-top: 5px; border-radius: 4px; overflow-x: auto;">${JSON.stringify(data.result, null, 2)}</pre>
                </div>
            `;
            // Trigger refresh of file list if applicable
            if (data.tool && (data.tool.includes('delete') || data.tool.includes('ingest'))) {
                loadStats();
                if (document.getElementById('files-view') && !document.getElementById('files-view').classList.contains('hidden')) {
                    loadFiles();
                }
            }
        } else if (data.status === 'denied') {
            // Update Card to Denied State
            card.style.borderColor = '#7f8c8d';
            card.style.background = 'rgba(127, 140, 141, 0.1)';
            card.innerHTML = `<div style="color: #95a5a6; font-weight: bold; text-align: center;">🚫 Action Denied</div>`;
        } else {
            // Error
            statusDiv.innerHTML = `<span style="color: red;">Error: ${data.error || 'Unknown error'}</span>`;
            buttons.forEach(btn => btn.disabled = false);
        }

    } catch (e) {
        console.error(e);
        statusDiv.innerHTML = `<span style="color: red;">Network Error: ${e.message}</span>`;
        buttons.forEach(btn => btn.disabled = false);
    }
}

function toggleDeepSearch() {
    isDeepSearchEnabled = !isDeepSearchEnabled;
    const btn = document.getElementById('deep-search-btn');
    if (btn) {
        if (isDeepSearchEnabled) {
            btn.style.opacity = '1';
            btn.style.boxShadow = '0 0 10px var(--accent-color)';
            btn.style.background = 'rgba(255,255,255,0.1)';
            showToast('Deep Search Enabled', 'info');
        } else {
            btn.style.opacity = '0.5';
            btn.style.boxShadow = 'none';
            btn.style.background = 'none';
            showToast('Deep Search Disabled', 'info');
        }
    }
}


// Initialize Bulk Delete Button Listener
// (Removed in favor of inline onclick for reliability)
// document.addEventListener('DOMContentLoaded', () => {
//     const btn = document.getElementById('bulk-delete-toggle-btn');
//     if (btn) {
//         btn.addEventListener('click', handleBulkDeleteClick);
//     }
// });

// ============== EXPORT GLOBALS ==============
// Export functions that need to be callable from index.html
window.initApp = initApp;
window.loadSessions = loadSessions;
window.checkHealth = checkHealth;
window.newChat = newChat;
window.sendMessage = sendMessage;
// window.showView // Handled by legacy.js
window.toggleSessionPin = toggleSessionPin;
window.deleteSession = deleteSession;
window.switchSession = switchSession;
window.toggleDeepSearch = toggleDeepSearch;
window.showSessionContextMenu = showSessionContextMenu;
window.showToast = showToast;
window.loadStats = loadStats;
window.toggleCompactMode = toggleCompactMode;
window.toggleCompactMode = toggleCompactMode;
window.generateExtensionToken = generateExtensionToken;
// window.loadFiles // Handled by modules.js

// ============== INITIALIZATION ==============
document.addEventListener('DOMContentLoaded', async () => {
    console.log("Onyx RAG Agent Initializing (v31)...");

    // 1. Check Backend Health & Ollama Status (Call directly)
    await checkHealth();

    // 1.5 Load Client Settings (Theme, Compact Mode)
    loadClientSettings();

    // 2. Load Settings (Populate UI)
    if (typeof loadSettings === 'function') await loadSettings();

    // 3. Load Sessions (Chat History)
    if (typeof loadSessions === 'function') await loadSessions();

    // Ensure empty state if no session logic (Consistent with New Chat)
    if (!currentSessionId && typeof toggleEmptyState === 'function') {
        toggleEmptyState(true);
    }

    // 4. Load Stats
    if (typeof loadStats === 'function') loadStats();

    // 5. Initial File Load (if view is active)
    if (typeof loadFiles === 'function') loadFiles();

    // 6. Polling for Status
    setInterval(() => {
        if (typeof checkHealth === 'function') checkHealth();
    }, 15000); // Poll every 15s for better responsiveness

});

// 7. Settings View Layout Fix (Independent Wrapper)
document.addEventListener('DOMContentLoaded', () => {
    // Poll for window.showView availability
    const initShowViewWrapper = () => {
        if (typeof window.showView === 'function') {
            const originalRefShowView = window.showView;
            if (originalRefShowView._isWrapped) return true;

            window.showView = function (viewName) {
                originalRefShowView(viewName);

                const mainContent = document.querySelector('.main-content');
                if (mainContent) {
                    if (viewName === 'settings') mainContent.classList.add('no-padding-bottom');
                    else mainContent.classList.remove('no-padding-bottom');
                }

                if (viewName === 'chat') {
                    setTimeout(() => {
                        if (typeof ensureScrollAnchor === 'function') ensureScrollAnchor();
                        if (typeof scrollToBottom === 'function') scrollToBottom();
                    }, 100);
                }
            };
            window.showView._isWrapped = true;
            return true;
        }
        return false;
    };

    if (!initShowViewWrapper()) {
        const wrapperInterval = setInterval(() => {
            if (initShowViewWrapper()) clearInterval(wrapperInterval);
        }, 50);
        setTimeout(() => clearInterval(wrapperInterval), 5000);
    }
});
