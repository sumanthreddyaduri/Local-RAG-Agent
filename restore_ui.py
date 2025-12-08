
import os

file_path = r'f:\RAG_Agent\local-rag-agent\templates\index.html'

# The complete, correct JavaScript to handle the UI
# Features:
# - No checkboxes in renderFiles
# - No bulk actions UI logic
# - Context Menu with correct escaping and dismissal
# - Robust deleteFile
# - Persistence and Theme

full_script = """    <script>
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
            
            // Only show skeleton if empty to avoid flashing
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
            
            // Hide bulk actions always
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
            // Disabled
        }
        
        function deleteSelectedFiles() {
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
                    showToast('Failed to delete file', 'error');
                }
            } catch (e) {
                showToast('Error deleting file', 'error');
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

        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme === 'light') {
                document.body.classList.add('light-theme');
                updateThemeIcon(true);
            }
            
            const lastView = localStorage.getItem('lastView');
            if (lastView) {
                setTimeout(() => showView(lastView), 100);
            }
            
            // Ensure context menu is in body
            const menu = document.getElementById('context-menu');
            if (menu && menu.parentNode !== document.body) {
                document.body.appendChild(menu);
            }
        });

        // Shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                const chatInput = document.getElementById('chat-input');
                if (document.activeElement === chatInput) sendMessage();
            }
            if (document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
                if (e.key === 's') { e.preventDefault(); document.getElementById('chat-input').focus(); }
                if (e.key === 'g') { fileViewMode = 'grid'; loadFiles(); }
                if (e.key === 'l') { fileViewMode = 'list'; loadFiles(); }
                if (e.key === '`') { document.getElementById('log-console')?.classList.toggle('visible'); }
            }
        });

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
        .file-list .file-actions {
            opacity: 0;
        }
        .file-list .file-card:hover .file-actions {
            opacity: 1;
        }
    </style>
</body>
</html>
"""

# Read existing file
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Locate where to cut. We'll cut before the LAST <script> tag (assuming it's the one we added).
# Actually, looking at the truncated file, the last script block starts around line 1620 (health check) AND THEN there was our appended block.
# If the file ends at "</body></html>", we should find the last </main> div closing.
# The structure is:
# ...
# </main>
# </div>
# <script>
# ... (original script)
# </script>
# <script>
# ... (our appended script)
# </script>
# <style>...</style>
# </body></html>

# If the file was truncated, we might have lost the appended script.
# We will append the new script BEFORE </body>.
# But first we should TRY to remove the old broken script if it exists.

# Let's find "</body>"
if "</body>" in content:
    # Check if we have the "FIXED & CONSOLIDATED" marker
    marker = "// ============== FIXED & CONSOLIDATED FEATURES"
    if marker in content:
        # Cut from there to the end
        parts = content.split(marker)
        # Keep everything before the marker, minus the <script> tag opening??
        # The marker was inside <script>.
        # Let's find the last <script> tag before the marker?
        # This is risky. 
        # Safer: Find "</body>" and replace everything from the last known good point?
        # Let's just find "</body>" and replace it with our new script + </body>.
        
        # But wait, if we duplicate the script, we get errors.
        # We need to remove the old one.
        
        # We just assume the current state is botched or clean-ish.
        # Let's replace the entire `</body>\n</html>` with our block.
        # AND we should aggressively strip any previous "FIXED" blocks if we can finding them.
        
        # Find the start of the FIXED block
        idx = content.find(marker)
        if idx != -1:
            # Find the <script> preceding it
            script_start = content.rfind("<script>", 0, idx)
            if script_start != -1:
                content = content[:script_start]
        
        # Now append
        # Ensure we strip </body></html> from the remaining content
        content = content.replace("</body>", "").replace("</html>", "").strip()
        
        content += "\n" + full_script
        
    else:
        # If marker not found (file truncated?), just append to the end (stripping body/html)
        content = content.replace("</body>", "").replace("</html>", "").strip()
        content += "\n" + full_script

else:
    # If </body> is missing, just append
    content += "\n" + full_script

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully restored UI logic with 'No Buttons' V4 configuration.")
