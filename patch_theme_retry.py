
import os

file_path = r'f:\RAG_Agent\local-rag-agent\templates\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add Toggle Button to Header
# Target: <button class="nav-btn" onclick="showView('settings')">⚙️ Settings</button>
target_btn = '<button class="nav-btn" onclick="showView(\'settings\')">⚙️ Settings</button>'
toggle_btn_html = """
            <button class="nav-btn" onclick="toggleTheme()" title="Toggle Theme">
                <span id="theme-icon">🌙</span>
            </button>
"""

if 'onclick="toggleTheme()"' not in content:
    if target_btn in content:
        content = content.replace(target_btn, toggle_btn_html + "\n            " + target_btn)
    else:
        print("Could not find Settings button to insert toggle next to. Content snippet:")
        # Print a snippet to debug
        start = content.find('class="top-actions"')
        if start != -1:
            print(content[start:start+500])
        else:
            print("Could not find top-actions div")

# 2. Add JavaScript Logic
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

print("Successfully patched theme toggle (retry).")
