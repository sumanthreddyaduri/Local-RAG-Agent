
import os
import re

file_path = r'f:\RAG_Agent\local-rag-agent\templates\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove Checkbox from renderFiles
# Pattern to match the checkbox input block
checkbox_pattern = r'<input type="checkbox" class="file-checkbox"[\s\S]*?onclick="event\.stopPropagation\(\); toggleFileSelection\(\'\$\{file\.name\}\', event\)">'
# We replace it with empty string
content = re.sub(checkbox_pattern, '', content)

# 2. Fix showContextMenu to escape IDs
# We will replace the function body start to include the escaping
context_menu_start = "function showContextMenu(event, type, id) {"
context_menu_fixed = """function showContextMenu(event, type, id) {
            event.preventDefault();
            event.stopPropagation();
            const menu = document.getElementById('context-menu');
            
            // Escape single quotes for inline onclick handlers
            const safeId = id.replace(/'/g, "\\\\'");
"""

content = content.replace(context_menu_start, context_menu_fixed)

# 3. Update the usage of 'id' to 'safeId' in the template string within showContextMenu
# We look for the specific block where items are defined
items_block = """items = `
                    <div class="context-menu-item" onclick="showPreview('${id}')">
                        👁️ Preview
                    </div>
                    <div class="context-menu-item danger" onclick="deleteFile('${id}')">
                        🗑️ Remove
                    </div>
                `;"""

items_block_fixed = """items = `
                    <div class="context-menu-item" onclick="showPreview('${safeId}')">
                        👁️ Preview
                    </div>
                    <div class="context-menu-item danger" onclick="deleteFile('${safeId}')">
                        🗑️ Remove
                    </div>
                `;"""

content = content.replace(items_block, items_block_fixed)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully applied UI fixes (removed checkbox, fixed context menu escaping)")
