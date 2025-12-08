
import os
import re

file_path = r'f:\RAG_Agent\local-rag-agent\templates\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# We will replace the consolidated script block we added earlier with the CORRECTED version.
# We can identify it by the start marker: "// ============== FIXED & CONSOLIDATED FEATURES =============="
# Or we can just strip everything after </body> and re-append.

# Let's find the start of our injected script
start_marker = "// ============== FIXED & CONSOLIDATED FEATURES =============="
script_start_idx = content.find(start_marker)

if script_start_idx != -1:
    # Find the <script> tag before this marker
    # We need to be careful. The marker is inside the script.
    # Let's look for <script> preceding it.
    script_tag_start = content.rfind("<script>", 0, script_start_idx)
    if script_tag_start != -1:
        # We will replace from this script tag to the end of the file (excluding </body></html>)
        # Actually, let's just truncate at script_tag_start and append the new correct script.
        content = content[:script_tag_start]
        
        # Also, we need to clean up the </body></html> tags if they were part of the mess
        # But my previous script appended them.
        # Let's just strip trailing whitespace and tags to be safe.
        content = content.rstrip()
        if content.endswith("</html>"):
            content = content[:-7].rstrip()
        if content.endswith("</body>"):
            content = content[:-7].rstrip()
else:
    # If we can't find our marker, maybe we are running on a fresh file?
    # Or maybe the previous script failed?
    # Let's assume we are appending to the body.
    if "</body>" in content:
        content = content.replace("</body>", "")
        content = content.replace("</html>", "")
    else:
        print("Warning: Could not find </body> tag.")

# Now we define the CORRECTED consolidated JS
corrected_js = """
    <script>
        // ============== FIXED & CONSOLIDATED FEATURES (v2) ==============

        // Global State
        let fileViewMode = 'grid';
        let selectedFiles = new Set();
        let currentContextFile = null; // For preview/ingest

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

        // 2. Loading States & Stats (Moved to top to be available globally)
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

        // 3. File Management (Fixed Uploads & Deletes)
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
            // Fix: Apply class to container, but ensure CSS exists
            container.className = fileViewMode === 'grid' ? 'file-grid' : 'file-list';
            
            // Update bulk actions visibility
            updateBulkActions();

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
                <div class="file-card ${selectedFiles.has(file.name) ? 'selected' : ''}" 
                     onclick="toggleFileSelection('${file.name}', event)"
                     oncontextmenu="showContextMenu(event, 'indexed', '${file.name}')"
                     ondblclick="showPreview('${file.name}')">
                    <input type="checkbox" class="file-checkbox" 
                           ${selectedFiles.has(file.name) ? 'checked' : ''}
                           onclick="event.stopPropagation(); toggleFileSelection('${file.name}', event)">
                    <div class="file-icon">${getFileIcon(file.name)}</div>
                    <div class="file-info">
                        <div class="file-name" title="${file.name}">${file.name}</div>
                        <div class="file-meta">${formatFileSize(file.size)} • ${formatDate(file.modified)}</div>
                    </div>
                </div>
            `).join('');
        }

        // Fix: Upload using correct API and FormData key
        async function uploadFiles(files) {
            if (!files || files.length === 0) return;

            const formData = new FormData();
            // Backend expects 'files' list
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
                console.error('Upload error:', e);
                showToast('Upload error: ' + e.message, 'error');
            }
        }

        // Drag & Drop Handlers
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
            event.target.value = ''; // Reset
        }

        // Fix: Bulk Delete using correct API
        async function deleteSelectedFiles() {
            if (selectedFiles.size === 0) return;
            
            if (!confirm(`Are you sure you want to delete ${selectedFiles.size} files?`)) return;
            
            const filesToDelete = Array.from(selectedFiles);
            
            try {
                const response = await fetch('/api/files/delete-multiple', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ files: filesToDelete })
                });
                const data = await response.json();
                
                if (data.status === 'success') {
                    showToast(`Deleted ${data.deleted.length} files`, 'success');
                    selectedFiles.clear();
                    loadFiles();
                    loadStats();
                } else {
                    showToast('Failed to delete some files', 'warning');
                    loadFiles();
                }
            } catch (e) {
                console.error('Bulk delete error:', e);
                showToast('Error deleting files', 'error');
            }
        }

        // Fix: Single Delete
        async function deleteFile(filename) {
            if (!confirm(`Delete "${filename}"?`)) return;
            
            try {
                const response = await fetch(`/api/files/${encodeURIComponent(filename)}`, {
                    method: 'DELETE'
                });
                const data = await response.json();
                
                if (data.status === 'success') {
                    selectedFiles.delete(filename);
                    loadFiles();
                    loadStats();
                    showToast('File deleted', 'success');
                } else {
                    showToast('Failed to delete file', 'error');
                }
            } catch (e) {
                showToast('Error deleting file', 'error');
            }
        }

        // 4. File Preview (Fixed Modal & Image URL)
        async function showPreview(filename) {
            currentContextFile = filename;
            const modal = document.getElementById('preview-modal');
            const content = document.getElementById('preview-content');
            const title = document.getElementById('preview-filename');
            
            title.textContent = filename;
            content.innerHTML = '<div class="loading">Loading preview...</div>';
            
            // Fix: Correctly toggle classes
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
                    // Fix: Use data.url instead of base64
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

        // Fix: Ingest from Preview
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

        // 5. View Navigation (Fixed Active States)
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
            
            // Fix: Better active state matching
            document.querySelectorAll('.nav-btn').forEach(btn => {
                btn.classList.remove('active');
                // Check onclick attribute content
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

        // 6. Helpers & Utilities
        function updateBulkActions() {
            const bulkActions = document.getElementById('bulk-actions');
            const selectedCount = document.getElementById('selected-count');
            if (bulkActions && selectedCount) {
                selectedCount.textContent = selectedFiles.size;
                if (selectedFiles.size > 0) {
                    bulkActions.classList.remove('hidden');
                } else {
                    bulkActions.classList.add('hidden');
                }
            }
        }

        function toggleFileSelection(filename, event) {
            if (event) event.stopPropagation();
            if (selectedFiles.has(filename)) {
                selectedFiles.delete(filename);
            } else {
                selectedFiles.add(filename);
            }
            // Re-render is expensive, let's just update the specific card class and checkbox
            // But for simplicity and correctness with bulk actions, re-render is safer for now.
            // Optimization: Just toggle class on element
            const card = event.currentTarget.closest('.file-card'); 
            // Actually, since we re-render, we don't need manual DOM manipulation.
            renderFiles(currentFilesList); // We need to store the list!
        }
        
        // We need to store the files list to avoid re-fetching on selection toggle
        let currentFilesList = [];
        const originalRenderFiles = renderFiles;
        renderFiles = function(files) {
            currentFilesList = files;
            originalRenderFiles(files);
        };

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
            
            let items = '';
            if (type === 'indexed') {
                items = `
                    <div class="context-menu-item" onclick="showPreview('${id}')">
                        👁️ Preview
                    </div>
                    <div class="context-menu-item danger" onclick="deleteFile('${id}')">
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

        document.addEventListener('click', () => {
            const menu = document.getElementById('context-menu');
            if (menu) menu.classList.remove('visible');
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
        /* Missing CSS for File List View */
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
            opacity: 0; /* Show on hover */
        }
        .file-list .file-card:hover .file-actions {
            opacity: 1;
        }
    </style>
</body>
</html>
"""

content += corrected_js

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully repaired UI logic in index.html")
