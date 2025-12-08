
import os
import re

file_path = r'f:\RAG_Agent\local-rag-agent\templates\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# ================= CSS =================
css_to_add = """
        /* Staged Files */
        .staged-files-section {
            margin-bottom: 30px;
            background-color: #252526;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }

        .staged-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }

        .staged-header h3 {
            margin: 0;
            color: var(--accent-color);
        }

        /* Context Menu */
        .context-menu {
            position: absolute;
            background-color: #2d2d2d;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            z-index: 10000;
            min-width: 150px;
            padding: 5px 0;
            display: none;
        }

        .context-menu.visible {
            display: block;
        }

        .context-menu-item {
            padding: 8px 15px;
            cursor: pointer;
            color: var(--text-color);
            font-size: 0.9em;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .context-menu-item:hover {
            background-color: var(--accent-color);
            color: white;
        }

        .context-menu-item.danger:hover {
            background-color: var(--error-color);
        }
"""

if "/* Staged Files */" not in content:
    content = content.replace("</style>", css_to_add + "\n    </style>")

# ================= HTML =================
# We will replace the entire #files-view content
# Find the start and end of #files-view
start_marker = '<div id="files-view" class="view-section hidden">'
end_marker = '<!-- File Preview Modal -->'

# Construct new HTML for files-view
new_html = """
            <div id="files-view" class="view-section hidden">
                <div class="file-manager">
                    <div class="file-manager-header">
                        <h2 style="margin: 0;">📁 File Manager</h2>
                        <div class="file-manager-actions">
                            <div class="view-toggle">
                                <button id="grid-view-btn" class="active" onclick="setFileView('grid')" title="Grid View">▦</button>
                                <button id="list-view-btn" onclick="setFileView('list')" title="List View">☰</button>
                            </div>
                            <button class="primary-btn" onclick="refreshFiles()" style="width: auto; margin: 0; padding: 8px 15px;">
                                🔄 Refresh
                            </button>
                        </div>
                    </div>

                    <!-- 1. Drop Zone (Top) -->
                    <div class="drop-zone" id="drop-zone" 
                         ondrop="handleDrop(event)" 
                         ondragover="handleDragOver(event)"
                         ondragleave="handleDragLeave(event)">
                        <div class="drop-zone-icon">📤</div>
                        <div class="drop-zone-text">Drag & drop files here to stage them</div>
                        <input type="file" id="file-input" multiple 
                               accept=".pdf,.txt,.md,.docx,.csv,.xlsx,.xls,.pptx,.ppt,.jpg,.jpeg,.png"
                               onchange="handleFileSelect(event)">
                        <button class="browse-btn" onclick="document.getElementById('file-input').click()">
                            Browse Files
                        </button>
                    </div>

                    <!-- 2. Staged Files Section -->
                    <div id="staged-files-section" class="staged-files-section hidden">
                        <div class="staged-header">
                            <h3>📋 Staged Files (Ready to Upload)</h3>
                            <button class="primary-btn" onclick="uploadStagedFiles()" style="width: auto; margin: 0;">
                                🚀 Upload to RAG
                            </button>
                        </div>
                        <div id="staged-file-grid" class="file-grid">
                            <!-- Staged files render here -->
                        </div>
                    </div>

                    <!-- 3. Indexed Files Section -->
                    <div class="indexed-files-section">
                        <h3 style="margin-bottom: 15px; border-bottom: 1px solid #3e3e42; padding-bottom: 10px;">
                            📚 Indexed Documents (Database)
                        </h3>
                        
                        <!-- Bulk Actions -->
                        <div class="bulk-actions hidden" id="bulk-actions">
                            <span class="selected-count"><span id="selected-count">0</span> files selected</span>
                            <div class="bulk-buttons">
                                <button class="primary-btn danger-btn" style="width: auto; margin: 0; padding: 8px 15px;"
                                    onclick="deleteSelectedFiles()">
                                    🗑️ Delete Selected
                                </button>
                                <button class="file-action-btn" onclick="clearSelection()">
                                    ✕ Clear Selection
                                </button>
                            </div>
                        </div>

                        <!-- File Grid Container -->
                        <div id="file-container">
                            <div class="file-grid" id="file-grid">
                                <!-- Indexed files load here -->
                            </div>
                        </div>

                        <!-- Empty State -->
                        <div class="empty-state hidden" id="empty-state">
                            <div class="empty-state-icon">📂</div>
                            <p>No documents indexed yet</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Context Menu -->
            <div id="context-menu" class="context-menu">
                <!-- Items injected dynamically -->
            </div>
"""

# Replace the block
# Use regex to find the block because exact string matching might fail due to whitespace
pattern = re.compile(r'<div id="files-view" class="view-section hidden">.*?<!-- File Preview Modal -->', re.DOTALL)
content = pattern.sub(new_html + "\n            <!-- File Preview Modal -->", content)


# ================= JavaScript =================
# We need to replace the file handling logic.
# We'll append the new logic at the end of the script block, overriding previous functions.
# Or better, we replace the specific functions.

js_to_add = """
        // ============== NEW File Manager Logic ==============
        let stagedFiles = [];
        let contextMenuTarget = null; // { type: 'staged'|'indexed', id: filename/index }

        // Override handleDrop
        async function handleDrop(event) {
            event.preventDefault();
            event.stopPropagation();
            document.getElementById('drop-zone').classList.remove('drag-over');
            const files = event.dataTransfer.files;
            stageFiles(files);
        }

        // Override handleFileSelect
        async function handleFileSelect(event) {
            const files = event.target.files;
            stageFiles(files);
            event.target.value = '';
        }

        function stageFiles(fileList) {
            if (!fileList.length) return;
            
            for (const file of fileList) {
                // Check duplicates in staged
                if (!stagedFiles.some(f => f.name === file.name)) {
                    stagedFiles.push(file);
                }
            }
            renderStagedFiles();
        }

        function renderStagedFiles() {
            const container = document.getElementById('staged-file-grid');
            const section = document.getElementById('staged-files-section');
            
            if (stagedFiles.length === 0) {
                section.classList.add('hidden');
                return;
            }
            
            section.classList.remove('hidden');
            container.innerHTML = stagedFiles.map((file, index) => `
                <div class="file-card" oncontextmenu="showContextMenu(event, 'staged', ${index})">
                    <div class="file-icon">${getFileIcon(file.name)}</div>
                    <div class="file-info">
                        <div class="file-name" title="${file.name}">${file.name}</div>
                        <div class="file-meta">${formatFileSize(file.size)}</div>
                    </div>
                    <div class="file-status" style="color: var(--warning-color); font-size: 0.8em; margin-top:5px;">Ready to Upload</div>
                </div>
            `).join('');
        }

        function removeStagedFile(index) {
            stagedFiles.splice(index, 1);
            renderStagedFiles();
        }

        async function uploadStagedFiles() {
            if (stagedFiles.length === 0) return;

            const btn = document.querySelector('#staged-files-section .primary-btn');
            const originalText = btn.innerText;
            btn.innerText = "⏳ Uploading...";
            btn.disabled = true;

            for (const file of stagedFiles) {
                const formData = new FormData();
                formData.append('document', file);

                try {
                    await fetch('/upload', {
                        method: 'POST',
                        body: formData
                    });
                } catch (e) {
                    console.error('Upload failed:', file.name, e);
                    alert(`Failed to upload ${file.name}`);
                }
            }

            stagedFiles = [];
            renderStagedFiles();
            loadFiles(); // Refresh indexed list
            loadStats();
            
            btn.innerText = originalText;
            btn.disabled = false;
        }

        // Context Menu Logic
        document.addEventListener('click', () => {
            document.getElementById('context-menu').classList.remove('visible');
        });

        document.addEventListener('contextmenu', (e) => {
            // Prevent default only if inside file manager
            if (e.target.closest('.file-card')) {
                e.preventDefault();
            }
        });

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

        // Update renderFiles to add context menu support
        // We need to override the previous renderFiles function entirely or patch it.
        // Since we are appending this JS, we can redefine renderFiles.
        
        renderFiles = function (files) {
            const container = document.getElementById('file-grid');
            container.className = fileViewMode === 'grid' ? 'file-grid' : 'file-list';

            // Update bulk actions visibility
            updateBulkActions();

            // Show/hide empty state
            const emptyState = document.getElementById('empty-state');
            const fileContainer = document.getElementById('file-container');
            
            if (files.length === 0) {
                if(emptyState) emptyState.classList.remove('hidden');
                if(fileContainer) fileContainer.classList.add('hidden');
                container.innerHTML = '';
                return;
            } else {
                if(emptyState) emptyState.classList.add('hidden');
                if(fileContainer) fileContainer.classList.remove('hidden');
            }

            container.innerHTML = files.map(file => `
                <div class="file-card ${selectedFiles.has(file.name) ? 'selected' : ''}" 
                     onclick="toggleFileSelection('${file.name}', event)"
                     oncontextmenu="showContextMenu(event, 'indexed', '${file.name}')"
                     ondblclick="showPreview('${file.name}')">
                    <input type="checkbox" class="file-checkbox" 
                           ${selectedFiles.has(file.name) ? 'checked' : ''}
                           onclick="event.stopPropagation(); toggleFileSelection('${file.name}', event)">
                    <div class="file-icon">${getFileIcon(file.name)}</div>
                    <div class="file-info">
                        <div class="file-name" title="${file.name}">${file.name}</div>
                        <div class="file-meta">${formatFileSize(file.size)} • ${formatDate(file.modified)}</div>
                    </div>
                </div>
            `).join('');
        };
"""

# Append JS before </body>
content = content.replace("</body>", "<script>\n" + js_to_add + "\n</script>\n</body>")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully patched File Manager in index.html")
