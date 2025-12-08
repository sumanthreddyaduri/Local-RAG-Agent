
import os

file_path = r'f:\RAG_Agent\local-rag-agent\templates\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add Skeleton CSS
skeleton_css = """
        /* Skeleton Loading */
        .skeleton {
            background: linear-gradient(90deg, #333 25%, #444 50%, #333 75%);
            background-size: 200% 100%;
            animation: shimmer 1.5s infinite;
            color: transparent !important;
            border-radius: 4px;
            min-height: 1em;
            display: inline-block;
            width: 100%;
        }
        
        @keyframes shimmer {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }
        
        body.light-theme .skeleton {
            background: linear-gradient(90deg, #e0e0e0 25%, #f0f0f0 50%, #e0e0e0 75%);
        }
"""

if "/* Skeleton Loading */" not in content:
    content = content.replace("</style>", skeleton_css + "\n    </style>")

# 2. Redefine loadStats and loadFiles
# We'll append these to the end to overwrite previous definitions.

js_logic = """
        // ============== Loading States ==============
        
        async function loadStats() {
            const ids = ['stat-docs', 'stat-chunks', 'stat-sessions', 'stat-messages'];
            ids.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.classList.add('skeleton');
            });
            
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                if (document.getElementById('stat-docs')) document.getElementById('stat-docs').innerText = data.total_documents || 0;
                if (document.getElementById('stat-chunks')) document.getElementById('stat-chunks').innerText = data.total_chunks || 0;
                if (document.getElementById('stat-sessions')) document.getElementById('stat-sessions').innerText = data.total_sessions || 0;
                if (document.getElementById('stat-messages')) document.getElementById('stat-messages').innerText = data.total_messages || 0;
                
                // Update chart if exists
                if (window.usageChart) {
                    updateChart(data);
                }
            } catch (e) {
                console.error('Failed to load stats:', e);
            } finally {
                ids.forEach(id => {
                    const el = document.getElementById(id);
                    if (el) el.classList.remove('skeleton');
                });
            }
        }

        async function loadFiles() {
            const container = document.getElementById('file-grid');
            if (!container) return;
            
            // Show skeleton in grid
            container.innerHTML = Array(3).fill(0).map(() => `
                <div class="file-card">
                    <div class="file-icon skeleton" style="width: 40px; height: 40px;"></div>
                    <div class="file-info" style="width: 100%">
                        <div class="file-name skeleton" style="width: 80%; margin-bottom: 5px;"></div>
                        <div class="file-meta skeleton" style="width: 50%;"></div>
                    </div>
                </div>
            `).join('');
            
            try {
                const response = await fetch('/api/files');
                const data = await response.json();
                renderFiles(data.files || []);
            } catch (e) {
                console.error('Failed to load files:', e);
                container.innerHTML = '<div class="empty-state"><p>Failed to load files</p></div>';
            }
        }
"""

content = content.replace("</script>", js_logic + "\n    </script>")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully patched loading states.")
