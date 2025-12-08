"""
Minimal test server for UI testing.
This bypasses the ML dependencies that have Python 3.14 compatibility issues.
"""
from flask import Flask, render_template, request, jsonify
import os
import json
from datetime import datetime

app = Flask(__name__)

# Mock data
UPLOAD_DIR = "./uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

sessions = [
    {"id": 1, "name": "Default Session", "title": "Session 1", "created_at": datetime.now().isoformat()},
]
current_session_id = 1
chat_history = []

# Load config
def load_config():
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except:
        return {
            "model": "gemma3:270m",
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "retrieval_k": 3,
            "use_hybrid_search": True,
            "hybrid_alpha": 0.5
        }

def save_config(config):
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)

config = load_config()

# Ensure config has all needed fields
config.setdefault('mode', 'browser')
config.setdefault('model', 'gemma3:270m')
config.setdefault('embed_model', 'all-MiniLM-L6-v2')
config.setdefault('chunk_size', 1000)
config.setdefault('chunk_overlap', 200)
config.setdefault('retrieval_k', 3)
config.setdefault('hybrid_alpha', 0.5)
config.setdefault('max_history_context', 5)

available_models = ['gemma3:270m', 'qwen2.5:0.5b', 'llama2', 'mistral']

def get_indexed_files():
    files = []
    if os.path.exists(UPLOAD_DIR):
        for f in os.listdir(UPLOAD_DIR):
            files.append(os.path.join(UPLOAD_DIR, f))
    return files

@app.route("/")
def index():
    return render_template("index.html", 
                         sessions=sessions,
                         current_session_id=current_session_id,
                         chat_history=chat_history,
                         config=config,
                         indexed_files=get_indexed_files(),
                         available_models=available_models,
                         status='',
                         message='')

@app.route("/api/health")
def health():
    return jsonify({
        "status": "healthy",
        "ollama": {"status": "mock", "message": "Test server - Ollama not connected"},
        "model": config.get("model", "gemma3:270m"),
        "index": {"documents": 2, "chunks": 10}
    })

@app.route("/api/settings", methods=["GET", "POST"])
def settings():
    global config
    if request.method == "GET":
        return jsonify(config)
    else:
        data = request.json
        config.update(data)
        save_config(config)
        return jsonify({"status": "success", "config": config})

@app.route("/api/sessions", methods=["GET", "POST"])
def sessions_api():
    global sessions, current_session_id
    if request.method == "GET":
        return jsonify({"sessions": sessions, "current_session_id": current_session_id})
    else:
        new_id = max(s["id"] for s in sessions) + 1 if sessions else 1
        new_session = {"id": new_id, "name": f"Session {new_id}", "title": f"Session {new_id}", "created_at": datetime.now().isoformat()}
        sessions.append(new_session)
        current_session_id = new_id
        return jsonify(new_session)

@app.route("/api/sessions/<int:session_id>", methods=["GET", "DELETE"])
def session_api(session_id):
    global sessions, current_session_id
    if request.method == "DELETE":
        sessions = [s for s in sessions if s["id"] != session_id]
        if current_session_id == session_id and sessions:
            current_session_id = sessions[0]["id"]
        return jsonify({"status": "deleted"})
    return jsonify({"session_id": session_id, "messages": []})

@app.route("/api/sessions/<int:session_id>/switch", methods=["POST"])
def switch_session(session_id):
    global current_session_id
    current_session_id = session_id
    return jsonify({"status": "switched", "session_id": session_id})

@app.route("/api/index/stats")
def index_stats():
    files = os.listdir(UPLOAD_DIR) if os.path.exists(UPLOAD_DIR) else []
    return jsonify({
        "total_documents": len(files),
        "total_files": len(files),
        "total_chunks": len(files) * 5,
        "files": files
    })

@app.route("/api/index/clear", methods=["POST"])
def clear_index():
    return jsonify({"status": "success", "message": "Index cleared (mock)"})

@app.route("/api/files", methods=["GET", "POST"])
def files_api():
    if request.method == "GET":
        files = []
        if os.path.exists(UPLOAD_DIR):
            for f in os.listdir(UPLOAD_DIR):
                path = os.path.join(UPLOAD_DIR, f)
                stat = os.stat(path)
                files.append({
                    "name": f,
                    "size": stat.st_size,
                    "modified": stat.st_mtime
                })
        return jsonify({"files": files})
    else:
        # Batch delete
        data = request.json
        if data.get("action") == "delete_batch":
            for fname in data.get("files", []):
                path = os.path.join(UPLOAD_DIR, fname)
                if os.path.exists(path):
                    os.remove(path)
        return jsonify({"status": "success"})

@app.route("/api/files/<path:filename>", methods=["DELETE"])
def delete_file(filename):
    path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(path):
        os.remove(path)
        return jsonify({"status": "deleted"})
    return jsonify({"error": "File not found"}), 404

@app.route("/api/files/<path:filename>/preview")
def preview_file(filename):
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        return jsonify({"error": "File not found"}), 404
    
    ext = os.path.splitext(filename)[1].lower()
    if ext in [".txt", ".md", ".csv", ".json", ".py", ".js", ".html", ".css"]:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(5000)
        return jsonify({"type": "text", "content": content})
    return jsonify({"type": "info", "content": f"Preview not available for {ext} files"})

@app.route("/api/files/<path:filename>/ingest", methods=["POST"])
def ingest_file(filename):
    return jsonify({"status": "success", "message": f"Ingested {filename} (mock)"})

@app.route("/upload", methods=["POST"])
def upload():
    if "document" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files["document"]
    if file.filename:
        path = os.path.join(UPLOAD_DIR, file.filename)
        file.save(path)
        return jsonify({"status": "success", "filename": file.filename})
    return jsonify({"error": "Empty filename"}), 400

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    message = data.get("message", "")
    
    def generate():
        response_text = f" [Mock] Received: '{message}'.\n\nThis is a test server response. The full RAG system requires Python 3.11/3.12."
        # Simulate streaming
        import time
        for word in response_text.split(" "):
            yield word + " "
            time.sleep(0.05)
    
    return app.response_class(generate(), mimetype='text/plain')

@app.route("/set_mode", methods=["POST"])
def set_mode():
    data = request.json
    mode = data.get("mode")
    config["mode"] = mode
    save_config(config)
    return jsonify({"status": "success", "mode": mode})

@app.route("/ocr", methods=["POST"])
def ocr():
    return jsonify({"warning": "OCR not available in test mode"})

if __name__ == "__main__":
    print("=" * 50)
    print("TEST SERVER - UI Testing Mode")
    print("=" * 50)
    print("This is a minimal server for testing the UI.")
    print("ML features are mocked due to Python 3.14 compatibility issues.")
    print("For full functionality, use Python 3.11 or 3.12.")
    print("=" * 50)
    print("\nOpen http://localhost:8501 in your browser\n")
    app.run(host="0.0.0.0", port=8501, debug=True)
