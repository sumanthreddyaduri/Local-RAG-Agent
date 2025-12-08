
import os

file_path = r'f:\RAG_Agent\local-rag-agent\templates\index.html'

# Valid V4 Script and Style WITH CSS
v4_script_style = """    <script>
        // ============== FIXED & CONSOLIDATED FEATURES (v4 Final) ==============

        // Global State
        let fileViewMode = 'grid';
        let selectedFiles = new Set();
        let currentContextFile = null;

        // 1. Theme Toggle
        function toggleTheme() {
            document.body.classList.toggle('light-theme');
            const isLight = document.body.classList.contains('light-theme');
            localStorage.setItem('theme', isLight ? 'light' : 'dark');
            updateThemeIcon(isLight);
        }

        function updateThemeIcon(isLight) {
            const icon = document.getElementById('theme-icon');
            if (icon) {
                icon.innerText = isLight ? '☀️' : '🌙';
            }
        }

        // 2. Loading States & Stats
        async function loadStats() {
            const ids = ['stat-docs', 'stat-chunks', 'stat-sessions', 'stat-messages'];
            ids.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.classList.add('skeleton');
            });
            
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
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

        // 3. File Management
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

            const emptyState = document.getElementById('empty-state');
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

        // 5. View Navigation
        showView = function(viewId) {
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
            
            document.querySelectorAll('.nav-btn').forEach(btn => {
                btn.classList.remove('active');
                const onclick = btn.getAttribute('onclick');
                if (onclick && onclick.includes(`'${viewId}'`)) {
                    btn.classList.add('active');
                }
            });

            if (viewId === 'files') loadFiles();
            if (viewId === 'dashboard') loadStats();
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
        
        window.alert = function(msg) { showToast(msg, 'warning'); };

        // Context Menu
        function showContextMenu(event, type, id) {
            event.preventDefault();
            event.stopPropagation();
            const menu = document.getElementById('context-menu');
            
            // Escape single quotes for inline onclick handlers
            const safeId = id.replace(/'/g, "\\\\'");
            
            let items = '';
            if (type === 'indexed') {
                items = `
                    <div class="context-menu-item" onclick="showPreview('${safeId}')">
                        👁️ Preview
                    </div>
                    <div class="context-menu-item danger" onclick="deleteFile('${safeId}')">
                        🗑️ Remove
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
        
        let currentMode = '{{ config.mode }}';
        let currentSessionId = {{ current_session_id or 'null' }};

        document.addEventListener('DOMContentLoaded', function () {
            checkHealth();
            if (currentMode === 'browser') {
                document.getElementById('btn-toggle').innerText = '🖥️ CLI Mode';
                showView('chat');
            } else {
                showView('control-panel');
            }
            const menu = document.getElementById('context-menu');
            if (menu && menu.parentNode !== document.body) {
                document.body.appendChild(menu);
            }
            setInterval(checkHealth, 30000);
        });

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

    </script>
    <style>
        .file-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .file-list .file-card {
            display: flex;
            flex-direction: row;
            align-items: center;
            width: 100%;
            height: auto;
            padding: 10px;
        }
        .file-list .file-icon {
            width: 30px;
            height: 30px;
            font-size: 1.2em;
            margin-bottom: 0;
            margin-right: 15px;
        }
        .file-list .file-info {
            flex: 1;
            text-align: left;
        }
        /* No file actions buttons */
        .file-actions { display: none !important; }
        
        /* Context Menu CSS */
        .context-menu {
            display: none;
            position: absolute;
            z-index: 9999;
            background-color: #252526;
            border: 1px solid #454545;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            min-width: 150px;
            border-radius: 4px;
            padding: 5px 0;
            color: #cccccc;
        }
        .context-menu.visible {
            display: block;
        }
        .context-menu-item {
            padding: 8px 15px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: background-color 0.2s;
            font-size: 14px;
        }
        .context-menu-item:hover {
            background-color: #37373d;
            color: #ffffff;
        }
        .context-menu-item.danger {
            color: #f14c4c;
        }
        .context-menu-item.danger:hover {
            background-color: rgba(241, 76, 76, 0.2);
            color: #ff6b6b;
        }
    </style>
</body>
</html>
"""

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# TRUNCATION STRATEGY:
# Find </main>
split_marker = "</main>"
if split_marker in content:
    parts = content.split(split_marker)
    base_content = parts[0] + "\n        </main>\n    </div>\n"
    new_content = base_content + v4_script_style
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully restored CSS for context menu.")
else:
    print("Error: Could not find split marker </main> in index.html. File might be corrupted.")
