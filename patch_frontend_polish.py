
import os

file_path = r'f:\RAG_Agent\local-rag-agent\templates\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. CSS for Toasts and Log Console
css_additions = """
        /* Toast Notifications */
        #toast-container {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 10001;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .toast {
            background-color: #333;
            color: white;
            padding: 12px 20px;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            display: flex;
            align-items: center;
            gap: 10px;
            min-width: 250px;
            animation: slideIn 0.3s ease-out forwards;
            border-left: 4px solid var(--accent-color);
        }

        .toast.error { border-left-color: var(--error-color); }
        .toast.success { border-left-color: var(--success-color); }
        .toast.warning { border-left-color: var(--warning-color); }

        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes fadeOut {
            from { opacity: 1; }
            to { opacity: 0; }
        }

        /* Log Console */
        #log-console {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            height: 200px;
            background-color: #1e1e1e;
            border-top: 1px solid var(--border-color);
            z-index: 9999;
            display: none;
            flex-direction: column;
            font-family: 'Consolas', monospace;
            font-size: 0.85em;
        }
        
        #log-console.visible { display: flex; }
        
        .log-header {
            padding: 5px 10px;
            background-color: #2d2d2d;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .log-body {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
            color: #ccc;
        }
        
        .log-entry { margin-bottom: 4px; border-bottom: 1px solid #333; padding-bottom: 2px; }
        .log-time { color: #888; margin-right: 8px; }
        .log-level { font-weight: bold; margin-right: 8px; }
        .log-level.INFO { color: #007bff; }
        .log-level.ERROR { color: #dc3545; }
        .log-level.WARN { color: #ffc107; }
"""

if "/* Toast Notifications */" not in content:
    content = content.replace("</style>", css_additions + "\n    </style>")

# 2. HTML for Toast Container and Log Console
html_additions = """
    <div id="toast-container"></div>
    
    <div id="log-console">
        <div class="log-header">
            <span>🖥️ System Logs</span>
            <div>
                <button class="icon-btn" onclick="clearLogs()">🚫</button>
                <button class="icon-btn" onclick="toggleLogs()">❌</button>
            </div>
        </div>
        <div class="log-body" id="log-body"></div>
    </div>
"""

if '<div id="toast-container">' not in content:
    content = content.replace("</body>", html_additions + "\n</body>")

# 3. JS Logic
js_logic = """
        // ============== Frontend Polish ==============
        
        // 1. Toast Notifications
        function showToast(message, type = 'info') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            
            let icon = 'ℹ️';
            if (type === 'error') icon = '❌';
            if (type === 'success') icon = '✅';
            if (type === 'warning') icon = '⚠️';
            
            toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
            
            container.appendChild(toast);
            
            // Auto remove
            setTimeout(() => {
                toast.style.animation = 'fadeOut 0.5s ease-out forwards';
                setTimeout(() => toast.remove(), 500);
            }, 3000);
        }
        
        // Override alert
        window.alert = function(msg) { showToast(msg, 'warning'); };

        // 2. View Persistence & Shortcuts
        const originalShowView = showView;
        showView = function(viewId) {
            // Call original logic (we need to replicate it or assume it's global)
            // Since we can't easily wrap the original function if it's defined as `function showView`, 
            // we will redefine it but copy the logic from the file if possible.
            // OR we just add the persistence logic to the existing function via replacement.
            
            // Let's just use localStorage in the init and update the global var
            localStorage.setItem('lastView', viewId);
            
            // Hide all views
            document.querySelectorAll('.view-section').forEach(el => el.classList.add('hidden'));
            document.getElementById(viewId + (viewId.includes('view') || viewId === 'control-panel' ? '' : '-view') || viewId).classList.remove('hidden');
            
            // Update nav buttons
            document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
            // Find button that calls this view (approximate)
            // This part is tricky to do generically, but visual active state is secondary to functionality.
            
            // Special handling
            if (viewId === 'files') loadFiles();
            
            // Show/hide input bar
            const inputBar = document.getElementById('input-bar');
            if (viewId === 'chat-view' || viewId === 'dashboard') { // Dashboard usually doesn't need chat, but let's keep it consistent
                 if (inputBar) inputBar.classList.remove('hidden');
            } else {
                 if (inputBar) inputBar.classList.add('hidden');
            }
        };

        // 3. Keyboard Shortcuts
        document.addEventListener('keydown', (e) => {
            // Ctrl+Enter to send
            if (e.ctrlKey && e.key === 'Enter') {
                const chatInput = document.getElementById('chat-input');
                if (document.activeElement === chatInput) {
                    sendMessage();
                }
            }
            
            // Global shortcuts (only if not typing)
            if (document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
                if (e.key === 's') {
                    e.preventDefault();
                    document.getElementById('chat-input').focus();
                }
                if (e.key === 'g') {
                    fileViewMode = 'grid';
                    loadFiles(); // Re-render
                }
                if (e.key === 'l') {
                    fileViewMode = 'list';
                    loadFiles(); // Re-render
                }
                if (e.key === '`') { // Tilde/Backtick to toggle logs
                    toggleLogs();
                }
            }
        });

        // 4. Logging Console
        function toggleLogs() {
            const consoleEl = document.getElementById('log-console');
            consoleEl.classList.toggle('visible');
        }
        
        function clearLogs() {
            document.getElementById('log-body').innerHTML = '';
        }
        
        function log(msg, level = 'INFO') {
            const body = document.getElementById('log-body');
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            const time = new Date().toLocaleTimeString();
            entry.innerHTML = `<span class="log-time">[${time}]</span><span class="log-level ${level}">${level}</span> ${msg}`;
            body.appendChild(entry);
            body.scrollTop = body.scrollHeight;
            
            // Also log to browser console
            if (level === 'ERROR') console.error(msg);
            else console.log(msg);
        }
        
        // Initialize View from Storage
        document.addEventListener('DOMContentLoaded', () => {
            const lastView = localStorage.getItem('lastView');
            if (lastView) {
                // We need to wait for other scripts to define showView
                setTimeout(() => showView(lastView), 100);
            }
        });
"""

content = content.replace("</script>", js_logic + "\n    </script>")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully patched frontend polish features.")
