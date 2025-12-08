
import os

file_path = r'f:\RAG_Agent\local-rag-agent\templates\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# We need to add loadFiles and refreshFiles functions.
# We can add them before the "NEW File Manager Logic" block or anywhere in the script.

js_to_add = """
        // ============== File Loading Logic ==============
        async function loadFiles() {
            try {
                const response = await fetch('/api/index/files');
                const data = await response.json();
                
                // The API returns { files: [...], count: N }
                // The files array contains strings (filenames)
                // We need to map them to objects for renderFiles if it expects objects
                // Let's check renderFiles implementation... 
                // It expects objects with .name, .size, .modified properties.
                // BUT /api/index/files only returns a list of strings!
                
                // Wait, /api/index/files returns indexed files (strings).
                // /api/files returns uploaded files with metadata!
                
                // The UI shows "Indexed Documents (Database)". 
                // If we want to show metadata, we should probably use /api/files 
                // and filter/mark those that are indexed.
                
                // Let's use /api/files which returns full metadata.
                const filesResponse = await fetch('/api/files');
                const filesData = await filesResponse.json();
                
                // filesData.files is an array of objects: {name, path, size, modified, indexed, ...}
                // We should filter for indexed ones if this section is strictly "Indexed Documents"
                // OR show all uploaded files and indicate which are indexed.
                // The header says "Indexed Documents (Database)".
                // But the user wants to see files they uploaded.
                
                // Let's show ALL uploaded files, but maybe highlight indexed ones?
                // Or just show indexed ones? 
                // The user complained "files are not visible... in indexed documents section".
                // If I use /api/index/files, I get strings. I can't show size/date.
                
                // BEST APPROACH: Use /api/files (which lists everything in uploaded_files dir)
                // and filter for those that are 'indexed': true (if the API supports it)
                // The /api/files endpoint in app.py checks 'indexed': filename in get_indexed_files()
                
                // So we use /api/files and filter for f.indexed === true?
                // Or just show all files in the "Indexed Documents" section?
                // Usually "Indexed Documents" implies what's in the DB.
                // But if a file is uploaded but not indexed, where does it go?
                // Ah, the new design has "Staged Files" (client side) and "Indexed Documents".
                // If a file is in 'uploaded_files' but not indexed, it's in limbo.
                
                // Let's show ALL files from /api/files in the "Indexed Documents" section
                // but maybe rename the header to "Uploaded Documents" if that's more accurate?
                // No, let's stick to "Indexed Documents" but show all files that are on the server.
                // Ideally, we should auto-index everything on upload.
                
                renderFiles(filesData.files);
                
            } catch (e) {
                console.error('Failed to load files:', e);
            }
        }

        function refreshFiles() {
            loadFiles();
            loadStats();
        }
"""

# Insert before "let stagedFiles = [];"
target = "let stagedFiles = [];"
if target in content:
    content = content.replace(target, js_to_add + "\n        " + target)
else:
    print("Could not find insertion point 'let stagedFiles = [];'")
    # Fallback: append to end of script
    content = content.replace("</script>", js_to_add + "\n    </script>")

# Also, we need to ensure loadFiles is called when the view is shown.
# Update showView to call loadFiles() if viewId === 'files'
if "if (viewId === 'dashboard') {" in content:
    content = content.replace(
        "if (viewId === 'dashboard') {", 
        "if (viewId === 'files') { loadFiles(); }\n            if (viewId === 'dashboard') {"
    )
else:
    print("Could not find showView dashboard check")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully patched loadFiles into index.html")
