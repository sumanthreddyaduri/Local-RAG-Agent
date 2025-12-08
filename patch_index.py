
import os

file_path = r'f:\RAG_Agent\local-rag-agent\templates\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Define the start and end markers for the block we want to replace
# We know loadStats is there, and showView ends around line 1468
# We will look for "let usageChart = null;" and replace until the end of showView

start_marker = "let usageChart = null;"
end_marker = "// ============== Settings =============="

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print("Could not find markers!")
    print(f"Start found: {start_idx}")
    print(f"End found: {end_idx}")
    exit(1)

new_content = """let usageChart = null;

        async function loadStats() {
            try {
                // Load index stats
                const indexResponse = await fetch('/api/index/stats');
                const indexData = await indexResponse.json();
                document.getElementById('chunk-count').innerText = indexData.total_chunks + ' chunks from ' + indexData.total_files + ' files';

                // Load usage stats
                const statsResponse = await fetch('/api/stats');
                const data = await statsResponse.json();

                // Update stat cards
                if(document.getElementById('stat-docs')) document.getElementById('stat-docs').innerText = data.total_documents;
                if(document.getElementById('stat-chunks')) document.getElementById('stat-chunks').innerText = data.total_chunks;
                if(document.getElementById('stat-sessions')) document.getElementById('stat-sessions').innerText = data.total_sessions;
                if(document.getElementById('stat-messages')) document.getElementById('stat-messages').innerText = data.total_messages;

                // Update Chart
                const ctx = document.getElementById('usageChart').getContext('2d');
                if (usageChart) {
                    usageChart.destroy();
                }

                usageChart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: ['Documents', 'Chunks', 'Sessions', 'Messages'],
                        datasets: [{
                            label: 'System Usage',
                            data: [data.total_documents, data.total_chunks, data.total_sessions, data.total_messages],
                            backgroundColor: [
                                'rgba(54, 162, 235, 0.6)',
                                'rgba(75, 192, 192, 0.6)',
                                'rgba(153, 102, 255, 0.6)',
                                'rgba(255, 159, 64, 0.6)'
                            ],
                            borderColor: [
                                'rgba(54, 162, 235, 1)',
                                'rgba(75, 192, 192, 1)',
                                'rgba(153, 102, 255, 1)',
                                'rgba(255, 159, 64, 1)'
                            ],
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: { beginAtZero: true, grid: { color: '#444' }, ticks: { color: '#ddd' } },
                            x: { grid: { color: '#444' }, ticks: { color: '#ddd' } }
                        },
                        plugins: {
                            legend: { labels: { color: '#ddd' } }
                        }
                    }
                });

            } catch (e) {
                console.error('Failed to load stats:', e);
            }
        }

        // ============== Mode Toggle ==============
        function toggleMode() {
            const btn = document.getElementById('btn-toggle');
            const status = document.getElementById('mode-status');

            if (currentMode === 'cli') {
                currentMode = 'browser';
                btn.innerText = '🖥️ CLI Mode';
                status.innerHTML = 'Mode: <strong>Browser Chat</strong>';
                showView('chat');
            } else {
                currentMode = 'cli';
                btn.innerText = '💬 Chat Mode';
                status.innerHTML = 'Mode: <strong>CLI Chat</strong>';
                showView('controls');
            }

            // Notify backend
            fetch('/set_mode', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode: currentMode })
            }).catch(console.error);
        }

        // ============== View Navigation ==============
        function showView(viewId) {
            // Hide all views
            document.querySelectorAll('.view-section').forEach(el => el.classList.add('hidden'));
            document.getElementById('input-bar').classList.add('hidden');

            // Show selected view
            const view = document.getElementById(viewId + '-view');
            if (view) {
                view.classList.remove('hidden');
            } else if (viewId === 'controls') {
                 // Fallback for controls if ID mismatch
                 const cp = document.getElementById('control-panel');
                 if(cp) cp.classList.remove('hidden');
            }

            // Show input bar only in chat view
            if (viewId === 'chat') {
                document.getElementById('input-bar').classList.remove('hidden');
                scrollToBottom();
            }

            // Update nav buttons
            document.querySelectorAll('.nav-btn').forEach(btn => {
                btn.classList.remove('active');
                if (btn.getAttribute('onclick')?.includes("'" + viewId + "'")) {
                    btn.classList.add('active');
                }
            });

            // Refresh stats if dashboard
            if (viewId === 'dashboard') {
                loadStats();
            }
        }

        """

final_content = content[:start_idx] + new_content + content[end_idx:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(final_content)

print("Successfully patched index.html")
