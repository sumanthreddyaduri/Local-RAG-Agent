
import os
import re

file_path = r'f:\RAG_Agent\local-rag-agent\templates\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Reset {% if message %} block
# We look for the block starting with {% if message %} and ending with {% endif %}
# And replace it with the clean version.
# Since the content inside might be huge and messy, we use a robust regex or string find.

start_marker = "{% if message %}"
end_marker = "{% endif %}"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)

if start_idx != -1 and end_idx != -1:
    # Extract the mess to verify (optional)
    # mess = content[start_idx:end_idx + len(end_marker)]
    
    clean_block = """{% if message %}
                    <div class="notification {{ status }}" id="notification">{{ message }}</div>
                    <script>
                        setTimeout(function () {
                            var el = document.getElementById('notification');
                            if (el) el.style.display = "none";
                        }, 5000);
                    </script>
                    {% endif %}"""
    
    content = content[:start_idx] + clean_block + content[end_idx + len(end_marker):]
    print("Reset {% if message %} block.")
else:
    print("Could not find {% if message %} block structure.")

# 2. Remove duplicate scripts at the end
# We'll look for the start of our injected scripts and truncate/replace.
# Markers: "// ============== Theme Toggle ==============" or "// ============== File Actions =============="
# We should remove everything from the first occurrence of these markers down to </body> (excluding </body>)
# But wait, we want to keep the ORIGINAL scripts (lines 1991+).
# The original scripts end around line 2700?
# My injected scripts usually start with a comment header.

# Let's just append the new consolidated script at the end of body.
# But we should try to clean up the mess if possible.
# If I appended to </script>, and there are multiple scripts, it's messy.
# Let's just append the new code. JS redefinitions will overwrite previous ones.
# The only risk is if there are syntax errors in the "messy" parts that are now outside the if-block?
# No, I removed the mess from the if-block.
# Are there other copies?
# If I ran the patch scripts multiple times, maybe.
# But let's assume the main mess was in the if-block.

# 3. Consolidated JS
consolidated_js = """
    <script>
        // ============== FIXED & CONSOLIDATED FEATURES ==============

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

        document.addEventListener('DOMContentLoaded', () => {
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme === 'light') {
                document.body.classList.add('light-theme');
                updateThemeIcon(true);
            }
        });

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
                
                // Update chart if exists
                if (window.usageChart) {
                    // We need to update the chart data
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

        async function loadFiles() {
            const container = document.getElementById('file-grid');
            if (!container) return;
            
            // Show skeleton
            container.innerHTML = Array(3).fill(0).map(() => `
                <div class="file-card">
                    <div class="file-icon skeleton" style="width: 40px; height: 40px;"></div>
                    <div class="file-info" style="width: 100%">
                        <div class="file-name skeleton" style="width: 80%; margin-bottom: 5px;"></div>
                        <div class="file-meta skeleton" style="width: 50%;"></div>
                    </div>
                </div>
            `).join('');
            
            try {
                const response = await fetch('/api/files');
                const data = await response.json();
                renderFiles(data.files || []);
            } catch (e) {
                console.error('Failed to load files:', e);
                container.innerHTML = '<div class="empty-state"><p>Failed to load files</p></div>';
            }
        }

        // 3. Frontend Polish (Toasts, Logs, View Persistence)
        function showToast(message, type = 'info') {
            const container = document.getElementById('toast-container');
            if (!container) return; // Should exist
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            
            let icon = 'ℹ️';
            if (type === 'error') icon = '❌';
            if (type === 'success') icon = '✅';
            if (type === 'warning') icon = '⚠️';
            
            toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
            
            container.appendChild(toast);
            
            setTimeout(() => {
                toast.style.animation = 'fadeOut 0.5s ease-out forwards';
                setTimeout(() => toast.remove(), 500);
            }, 3000);
        }
        
        window.alert = function(msg) { showToast(msg, 'warning'); };

        // Fixed showView
        // We don't use 'const originalShowView' because it causes issues if run multiple times.
        // We just redefine it completely.
        
        // Save the OLD showView if we haven't already, just in case (optional)
        // window.oldShowView = window.oldShowView || showView;

        showView = function(viewId) {
            localStorage.setItem('lastView', viewId);
            
            // Hide all views
            document.querySelectorAll('.view-section').forEach(el => el.classList.add('hidden'));
            document.getElementById('input-bar').classList.add('hidden');

            // Determine target ID
            let targetId = viewId + '-view';
            if (viewId === 'controls') targetId = 'control-panel';
            if (viewId === 'dashboard') targetId = 'dashboard-view';
            if (viewId === 'files') targetId = 'files-view';
            if (viewId === 'chat') targetId = 'chat-view';
            if (viewId === 'settings') targetId = 'settings-view';

            const target = document.getElementById(targetId);
            if (target) target.classList.remove('hidden');
            
            // Update nav buttons
            document.querySelectorAll('.nav-btn').forEach(btn => {
                btn.classList.remove('active');
                // Simple check for onclick content
                if (btn.getAttribute('onclick')?.includes(`'${viewId}'`)) {
                    btn.classList.add('active');
                }
            });

            // Special handling
            if (viewId === 'files') loadFiles();
            if (viewId === 'dashboard') loadStats();
            if (viewId === 'chat') {
                document.getElementById('input-bar').classList.remove('hidden');
                scrollToBottom();
            }
        };

        // Shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                const chatInput = document.getElementById('chat-input');
                if (document.activeElement === chatInput) sendMessage();
            }
            
            if (document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
                if (e.key === 's') { e.preventDefault(); document.getElementById('chat-input').focus(); }
                if (e.key === 'g') { setFileView('grid'); }
                if (e.key === 'l') { setFileView('list'); }
                if (e.key === '`') { toggleLogs(); }
            }
        });

        // Logs
        function toggleLogs() {
            const consoleEl = document.getElementById('log-console');
            if (consoleEl) consoleEl.classList.toggle('visible');
        }
        
        function clearLogs() {
            const body = document.getElementById('log-body');
            if (body) body.innerHTML = '';
        }
        
        function log(msg, level = 'INFO') {
            const body = document.getElementById('log-body');
            if (!body) return;
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            const time = new Date().toLocaleTimeString();
            entry.innerHTML = `<span class="log-time">[${time}]</span><span class="log-level ${level}">${level}</span> ${msg}`;
            body.appendChild(entry);
            body.scrollTop = body.scrollHeight;
            if (level === 'ERROR') console.error(msg);
            else console.log(msg);
        }

        // Initialize View
        document.addEventListener('DOMContentLoaded', () => {
            const lastView = localStorage.getItem('lastView');
            if (lastView) {
                setTimeout(() => showView(lastView), 100);
            }
        });

        // 4. Context Menu & File Actions
        // Re-injecting these because they were trapped in the if-block
        
        // We need to make sure we don't duplicate renderFiles logic if it's already there?
        // The original renderFiles (line 2444) didn't have context menu attributes.
        // So we MUST redefine it.

        renderFiles = function(files) {
            const container = document.getElementById('file-grid');
            container.className = fileViewMode === 'grid' ? 'file-grid' : 'file-list';

            // Update bulk actions visibility
            if (typeof updateBulkActions === 'function') updateBulkActions();

            // Show/hide empty state
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
        };

        function showContextMenu(event, type, id) {
            event.preventDefault();
            event.stopPropagation();

            const menu = document.getElementById('context-menu');
            contextMenuTarget = { type, id };

            let items = '';
            if (type === 'staged') {
                items = `
                    <div class="context-menu-item danger" onclick="removeStagedFile(${id})">
                        🗑️ Remove
                    </div>
                `;
            } else if (type === 'indexed') {
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
            
            menu.style.visibility = 'hidden';
            menu.style.display = 'block';
            menu.classList.add('visible');
            
            const rect = menu.getBoundingClientRect();
            const winWidth = window.innerWidth;
            const winHeight = window.innerHeight;
            
            if (x + rect.width > winWidth) x = winWidth - rect.width - 10;
            if (y + rect.height > winHeight) y = winHeight - rect.height - 10;
            
            menu.style.top = `${y}px`;
            menu.style.left = `${x}px`;
            menu.style.visibility = 'visible';
        }

        // Hide context menu on click
        document.addEventListener('click', () => {
            const menu = document.getElementById('context-menu');
            if (menu) menu.classList.remove('visible');
        });
        
        // Ensure context menu is in body
        document.addEventListener('DOMContentLoaded', () => {
            const menu = document.getElementById('context-menu');
            if (menu && menu.parentNode !== document.body) {
                document.body.appendChild(menu);
            }
        });

    </script>
"""

content = content.replace("</body>", consolidated_js + "\n</body>")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully cleaned and patched index.html")
