
import os

file_path = r'f:\RAG_Agent\local-rag-agent\templates\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# We need to remove the duplicate lines in showContextMenu
# The duplicate block looks like:
#             event.preventDefault();
#             event.stopPropagation();
#             const menu = document.getElementById('context-menu');

# We will read the file and filter out the specific duplicate block if it appears immediately after the first one (separated by the safeId line).

new_lines = []
skip_count = 0

for i, line in enumerate(lines):
    if skip_count > 0:
        skip_count -= 1
        continue
        
    # Check for the specific duplicate sequence starting at line 3921 (approx)
    # The pattern we saw:
    # 3919:             const safeId = id.replace(/'/g, "\\'");
    # 3920: 
    # 3921:             event.preventDefault();
    # 3922:             event.stopPropagation();
    # 3923:             const menu = document.getElementById('context-menu');
    
    if "const safeId = id.replace(/'/g, \"\\\\'\");" in line:
        new_lines.append(line)
        # Look ahead for duplicates
        if i + 3 < len(lines) and "event.preventDefault();" in lines[i+2] and "const menu =" in lines[i+4]:
             # This is a loose check, let's be more specific based on the file content I saw
             pass
    
    # Actually, let's just remove the specific duplicate lines if they exist in that exact order
    # But line numbers might shift.
    
    # Let's use a simpler approach: Read the whole content and replace the bad block with the good block.
    pass

content = "".join(lines)

bad_block = """            // Escape single quotes for inline onclick handlers
            const safeId = id.replace(/'/g, "\\\\'");

            event.preventDefault();
            event.stopPropagation();
            const menu = document.getElementById('context-menu');"""

good_block = """            // Escape single quotes for inline onclick handlers
            const safeId = id.replace(/'/g, "\\\\'");"""

if bad_block in content:
    content = content.replace(bad_block, good_block)
    print("Fixed duplicate code block.")
else:
    # Try to match with flexible whitespace if needed, but exact match should work based on previous view_file
    # Let's try to find the duplicate declarations manually
    pass

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
