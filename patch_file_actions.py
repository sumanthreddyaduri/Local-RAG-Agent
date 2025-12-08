
import os

file_path = r'f:\RAG_Agent\local-rag-agent\templates\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add CSS for context menu
css_to_add = """
        /* Context Menu */
        .context-menu {
            display: none;
            position: fixed; /* Fixed positioning to be relative to viewport */
            z-index: 10000;
            background-color: #2d2d2d;
            border: 1px solid #454545;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
            min-width: 150px;
            padding: 5px 0;
        }

        .context-menu.visible {
            display: block;
        }

        .context-menu-item {
            padding: 8px 15px;
            cursor: pointer;
            color: #e0e0e0;
            font-size: 0.9em;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: background-color 0.2s;
        }

        .context-menu-item:hover {
            background-color: #3d3d3d;
        }

        .context-menu-item.danger {
            color: #ff6b6b;
        }

        .context-menu-item.danger:hover {
            background-color: rgba(255, 107, 107, 0.1);
        }
"""

# Insert CSS before </style>
if "/* Context Menu */" not in content:
    content = content.replace("</style>", css_to_add + "\n    </style>")

# 2. Add JS functions
js_to_add = """
        // ============== File Actions ==============
        async function deleteFile(filename) {
            if (!confirm(`Are you sure you want to delete "${filename}"?`)) return;
            
            try {
                const response = await fetch(`/api/files/${encodeURIComponent(filename)}`, {
                    method: 'DELETE'
                });
                const data = await response.json();
                
                if (data.status === 'success') {
                    // Remove from selection if present
                    if (selectedFiles.has(filename)) {
                        selectedFiles.delete(filename);
                    }
                    loadFiles();
                    loadStats();
                } else {
                    alert('Failed to delete file: ' + (data.error || 'Unknown error'));
                }
            } catch (e) {
                console.error('Delete error:', e);
                alert('Error deleting file');
            }
        }

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
                    selectedFiles.clear();
                    loadFiles();
                    loadStats();
                } else {
                    alert('Failed to delete some files: ' + (data.message || 'Unknown error'));
                    loadFiles(); // Reload anyway to show what's left
                }
            } catch (e) {
                console.error('Bulk delete error:', e);
                alert('Error deleting files');
            }
        }
"""

# Insert JS before "function showContextMenu" (or anywhere appropriate)
# Since showContextMenu is already defined, let's append these functions before it or replace it.
# Actually, let's just append them to the end of the script block, or before the closing </script>.
# But we also need to update showContextMenu to use clientX/Y.

# 3. Update showContextMenu
# We'll replace the existing showContextMenu function.
old_show_context_menu = """
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
            menu.style.top = `${event.pageY}px`;
            menu.style.left = `${event.pageX}px`;
            menu.classList.add('visible');
        }
"""

# We need to be careful with exact string matching. 
# The indentation in the file might be different.
# Let's use a regex or just overwrite the function if we can find a unique signature.
# Or simpler: we append the new definition at the end, which will overwrite the previous one (JS hoisting/redefinition).
# But `showContextMenu` is defined as `function showContextMenu...` so it's hoisted. 
# If we define it again later, the second one wins.

new_show_context_menu = """
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
            
            // Use clientX/Y for fixed positioning
            // Also ensure it doesn't go off screen
            let x = event.clientX;
            let y = event.clientY;
            
            // Basic boundary check (optional, but good)
            // We can't check menu.offsetWidth yet because it's not visible/rendered
            // So just set it for now.
            
            menu.style.top = `${y}px`;
            menu.style.left = `${x}px`;
            menu.classList.add('visible');
        }
"""

# Append JS functions and the new showContextMenu
content = content.replace("</script>", js_to_add + "\n" + new_show_context_menu + "\n    </script>")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully patched file actions and context menu.")
