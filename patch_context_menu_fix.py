
import os

file_path = r'f:\RAG_Agent\local-rag-agent\templates\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Move context menu to body on load
# We'll add this to the window.onload or just run it at the end of the script.
move_menu_js = """
        // Ensure context menu is a direct child of body to avoid positioning issues
        document.addEventListener('DOMContentLoaded', () => {
            const menu = document.getElementById('context-menu');
            if (menu && menu.parentNode !== document.body) {
                document.body.appendChild(menu);
            }
        });
"""

# 2. Update showContextMenu to be more robust
# We will redefine it again at the end of the script to override previous definitions.
# We also add a click listener to the document to close the menu, which is already there but let's be sure.

robust_show_context_menu = """
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
                // Pass the filename (id) to deleteFile
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
            
            // Calculate position
            // Use clientX/Y for fixed positioning
            let x = event.clientX;
            let y = event.clientY;
            
            // Adjust if menu goes off screen
            // We need to show it first to get dimensions
            menu.style.visibility = 'hidden';
            menu.style.display = 'block';
            menu.classList.add('visible');
            
            const rect = menu.getBoundingClientRect();
            const winWidth = window.innerWidth;
            const winHeight = window.innerHeight;
            
            if (x + rect.width > winWidth) {
                x = winWidth - rect.width - 10;
            }
            
            if (y + rect.height > winHeight) {
                y = winHeight - rect.height - 10;
            }
            
            menu.style.top = `${y}px`;
            menu.style.left = `${x}px`;
            menu.style.visibility = 'visible';
        }
"""

# Append to the end of the script
content = content.replace("</script>", move_menu_js + "\n" + robust_show_context_menu + "\n    </script>")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully patched context menu positioning.")
