
import os

file_path = r'f:\RAG_Agent\local-rag-agent\templates\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add CSS
css_to_add = """
        /* Dashboard Stats */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background-color: #333;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }

        .stat-value {
            font-size: 2em;
            font-weight: bold;
            color: var(--accent-color);
            margin-bottom: 5px;
        }

        .stat-label {
            color: var(--text-secondary);
            font-size: 0.9em;
        }

        .chart-container {
            position: relative;
            height: 300px;
            width: 100%;
        }
"""

# Insert CSS before /* Header */
css_marker = "/* Header */"
if css_marker in content:
    content = content.replace(css_marker, css_to_add + "\n        " + css_marker)
else:
    print("CSS marker not found")

# 2. Add HTML
html_to_add = """
            <!-- Dashboard View -->
            <div id="dashboard-view" class="view-section hidden">
                <div class="control-card" style="max-width: 900px;">
                    <h2>📊 Analytics Dashboard</h2>
                    
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-value" id="stat-docs">-</div>
                            <div class="stat-label">Documents</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value" id="stat-chunks">-</div>
                            <div class="stat-label">Chunks</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value" id="stat-sessions">-</div>
                            <div class="stat-label">Sessions</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value" id="stat-messages">-</div>
                            <div class="stat-label">Messages</div>
                        </div>
                    </div>

                    <div class="chart-container">
                        <canvas id="usageChart"></canvas>
                    </div>
                </div>
            </div>
"""

# Insert HTML after <main class="main-content">
html_marker = '<main class="main-content">'
if html_marker in content:
    content = content.replace(html_marker, html_marker + "\n" + html_to_add)
else:
    print("HTML marker not found")

# 3. Add Dashboard Button to Header if missing
# Check if "Dashboard" button exists
if "Dashboard" not in content and "showView('dashboard')" not in content:
    # Add it before Controls button
    btn_marker = '<button class="nav-btn" onclick="showView(\'control-panel\')">📂 Controls</button>'
    btn_html = '<button class="nav-btn" onclick="showView(\'dashboard\')">📊 Dashboard</button>'
    
    if btn_marker in content:
        content = content.replace(btn_marker, btn_html + "\n            " + btn_marker)
    else:
        print("Button marker not found")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully patched dashboard into index.html")
