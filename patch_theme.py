
import os

file_path = r'f:\RAG_Agent\local-rag-agent\templates\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add Light Theme CSS
light_theme_css = """
        /* Light Theme */
        body.light-theme {
            --bg-color: #f0f2f5;
            --sidebar-bg: #ffffff;
            --header-bg: #ffffff;
            --card-bg: #ffffff;
            --text-color: #333333;
            --text-secondary: #666666;
            --border-color: #e0e0e0;
        }
        
        body.light-theme .stat-card,
        body.light-theme .file-card,
        body.light-theme .control-card,
        body.light-theme .chat-message.bot-message,
        body.light-theme .history-item {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        body.light-theme .nav-btn {
            background-color: #f0f0f0;
            color: #333;
            border-color: #d0d0d0;
        }
        
        body.light-theme .nav-btn:hover {
            background-color: #e0e0e0;
        }
        
        body.light-theme .nav-btn.active {
            background-color: var(--accent-color);
            color: white;
        }
        
        body.light-theme .input-container {
            background-color: #ffffff;
            border: 1px solid #d0d0d0;
        }
        
        body.light-theme #chat-input {
            color: #333;
        }
"""

if "/* Light Theme */" not in content:
    content = content.replace("</style>", light_theme_css + "\n    </style>")

# 2. Add Toggle Button to Header
# We'll add it before the Settings button
toggle_btn_html = """
            <button class="nav-btn" onclick="toggleTheme()" title="Toggle Theme">
                <span id="theme-icon">🌙</span>
            </button>
"""

if 'onclick="toggleTheme()"' not in content:
    # Find the Settings button
    settings_btn = '<button class="nav-btn" id="btn-settings" onclick="showView(\'settings\')">'
    if settings_btn in content:
        content = content.replace(settings_btn, toggle_btn_html + "\n            " + settings_btn)
    else:
        print("Could not find Settings button to insert toggle next to.")

# 3. Add JavaScript Logic
js_logic = """
        // ============== Theme Toggle ==============
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

        // Initialize Theme
        document.addEventListener('DOMContentLoaded', () => {
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme === 'light') {
                document.body.classList.add('light-theme');
                updateThemeIcon(true);
            }
        });
"""

if "function toggleTheme()" not in content:
    content = content.replace("</script>", js_logic + "\n    </script>")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully patched theme toggle.")
