
import os

file_path = r'f:\RAG_Agent\local-rag-agent\templates\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Define the block to remove
# We'll look for the start and end of the div
start_marker = '<div class="indexed-files">'
end_marker = '</div>' # This is too generic, we need to be careful.

# Let's use the content we know is inside
target_block_start = '<div class="indexed-files">'
target_content_inside = '<h3>📚 Indexed Documents</h3>'

if target_block_start in content and target_content_inside in content:
    # Find start index
    start_idx = content.find(target_block_start)
    
    # Find the closing div for this block. 
    # Since it contains nested divs, we need to count braces or just look for the specific structure.
    # The structure is:
    # <div class="indexed-files">
    #     ...
    # </div>
    # It ends before </aside>
    
    sidebar_end = content.find('</aside>', start_idx)
    
    if sidebar_end != -1:
        # We can just remove everything from start_idx to sidebar_end (excluding sidebar_end)
        # But wait, is there anything else in the sidebar after this?
        # Looking at previous view_file, it seems to be the last item in sidebar.
        
        # Let's verify what's being removed
        to_remove = content[start_idx:sidebar_end]
        # print(f"Removing:\n{to_remove}")
        
        new_content = content[:start_idx] + content[sidebar_end:]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Successfully removed indexed-files from sidebar.")
    else:
        print("Could not find end of sidebar.")
else:
    print("Could not find indexed-files block.")
