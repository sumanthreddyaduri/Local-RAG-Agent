
import os
import re

file_path = r'f:\RAG_Agent\local-rag-agent\templates\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove Selection Logic & Bulk Actions
# We replace toggleFileSelection with a dummy that just opens preview on double click (which is handled separately anyway)
# Or better, we make single click do nothing or select for preview context? 
# The user wants "Delete Selected" gone. So we just stop adding to selectedFiles.

# Replace toggleFileSelection function
toggle_func_pattern = r'function toggleFileSelection\(filename, event\) \{[\s\S]*?renderFiles\(currentFilesList\); // We need to store the list!\s*\}'
toggle_func_replacement = """function toggleFileSelection(filename, event) {
            // Selection disabled as per user request
            if (event) event.stopPropagation();
        }"""
content = re.sub(toggle_func_pattern, toggle_func_replacement, content)

# Remove updateBulkActions call in renderFiles
content = content.replace("updateBulkActions();", "// updateBulkActions();")

# Hide the bulk actions div permanently just in case
content = content.replace('<div id="bulk-actions"', '<div id="bulk-actions" style="display:none!important;"')

# 2. Fix Context Menu Dismissal
# The current listener is:
# document.addEventListener('click', () => {
#     const menu = document.getElementById('context-menu');
#     if (menu) menu.classList.remove('visible');
# });
# This looks correct, but maybe z-index or propagation issue.
# I will make it more robust.

dismiss_pattern = r"document\.addEventListener\('click', \(\) => \{\s*const menu = document\.getElementById\('context-menu'\);\s*if \(menu\) menu\.classList\.remove\('visible'\);\s*\}\);"
dismiss_replacement = """
        // Close context menu on any click outside
        window.addEventListener('click', (e) => {
            const menu = document.getElementById('context-menu');
            if (menu && menu.classList.contains('visible')) {
                // If click is inside menu, do nothing (handled by items)
                // Actually items have their own handlers, so we can just close it active.
                // But let's check if target is inside menu
                if (!menu.contains(e.target)) {
                    menu.classList.remove('visible');
                    menu.style.display = 'none'; // Ensure it hides
                }
            }
        });
"""
content = content.replace(dismiss_pattern, dismiss_replacement)

# Also update showContextMenu to remove the display:block style when showing, relies on class?
# The CSS probably handles .visible. But let's check showContextMenu.
# It sets menu.style.display = 'block'; and menu.classList.add('visible');
# We should ensure we reset display to none when closing.

# 3. Fix Delete File
# The function deleteFile(filename) calls /api/files/filename
# User said "delete button does not remove the file".
# Maybe the filename has issues.
# I will add console logs to deleteFile to debug.

delete_func_pattern = r'async function deleteFile\(filename\) \{[\s\S]*?catch \(e\) \{\s*showToast\(\'Error deleting file\', \'error\'\);\s*\}\s*\}'
delete_func_replacement = """async function deleteFile(filename) {
            if (!confirm(`Delete "${filename}"?`)) return;
            
            console.log("Attempting to delete:", filename);
            showToast('Deleting...', 'info');

            try {
                // Fix: Ensure filename is correctly encoded
                const response = await fetch(`/api/files/${encodeURIComponent(filename)}`, {
                    method: 'DELETE'
                });
                console.log("Delete response status:", response.status);
                const data = await response.json();
                console.log("Delete response data:", data);
                
                if (data.status === 'success') {
                    // Update UI immediately without waiting for reload
                    selectedFiles.delete(filename);
                    loadFiles();
                    loadStats();
                    showToast('File deleted successfully', 'success');
                    
                    // Close menu
                    const menu = document.getElementById('context-menu');
                    if (menu) {
                        menu.classList.remove('visible');
                        menu.style.display = 'none';
                    }
                } else {
                    showToast('Failed to delete: ' + (data.message || data.error), 'error');
                }
            } catch (e) {
                console.error("Delete error:", e);
                showToast('Error deleting file: ' + e.message, 'error');
            }
        }"""

content = re.sub(delete_func_pattern, delete_func_replacement, content)

# 4. Remove onclick from file card main div to prevent selection (moved to toggleFileSelection replacement above as dummy)
# But we can also just remove the click handler from HTML generation to be cleaner.
# <div class="file-card ..." onclick="toggleFileSelection...">
# We will remove the onclick attribute from the template literal in renderFiles.

content = content.replace("onclick=\"toggleFileSelection('${file.name}', event)\"", "")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Applied fix_ui_v3: Disabled selection, hid bulk actions, improved menu dismissal and delete logging.")
