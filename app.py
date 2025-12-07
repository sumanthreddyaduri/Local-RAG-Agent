"""
Enhanced Flask Application with Persistent Chat Memory, Health Checks, and Improved Error Handling.
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
import os
import json
import traceback
from backend import ingest_files, get_rag_chain, clear_index, get_indexed_files, get_index_stats
from config_manager import load_config, save_config, update_config, DEFAULT_CONFIG, validate_config
from database import (
    get_or_create_default_session, create_session, get_all_sessions,
    add_message, get_messages, format_history_for_prompt, 
    delete_session, rename_session, clear_session_messages
)
from health_check import check_ollama_health, check_model_available, get_system_status
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from PIL import Image
import pytesseract

app = Flask(__name__)
UPLOAD_DIR = "./uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Current active session (thread-safe would require Flask-Login or similar in production)
CURRENT_SESSION_ID = None


def get_current_session():
    """Get or create the current chat session."""
    global CURRENT_SESSION_ID
    if CURRENT_SESSION_ID is None:
        CURRENT_SESSION_ID = get_or_create_default_session()
    return CURRENT_SESSION_ID

def format_docs(docs):
    """Format retrieved documents with source information."""
    formatted = []
    for doc in docs:
        source = doc.metadata.get('source', 'Unknown')
        content = doc.page_content
        formatted.append(f"Source: {source}\nContent: {content}")
    return "\n\n".join(formatted)


@app.route("/chat", methods=["POST"])
def chat():
    """Handle chat messages with persistent history and streaming responses."""
    try:
        data = request.json
        query = data.get("message", "").strip()
        
        if not query:
            return jsonify({"error": "Empty message"}), 400
        
        config = load_config()
        model_name = config.get("model", "gemma3:270m")
        max_history = config.get("max_history_context", 10)
        show_sources = config.get("show_sources", True)
        
        session_id = data.get("session_id") or get_current_session()
        
        # Check Ollama health before attempting chat
        health = check_ollama_health(config.get("ollama_host", "http://localhost:11434"))
        if not health["available"]:
            return jsonify({"error": f"Ollama is not available: {health['error']}"}), 503
        
        retriever, llm = get_rag_chain(model_name)
        
        # Get conversation history from database
        history_text = format_history_for_prompt(session_id, max_history)
        
        if retriever is None:
            template = """You are a helpful AI assistant. Answer the question based on the conversation history.

Conversation History:
{history}

User Question: {question}

Provide a helpful and informative response."""
            chain = (
                {"question": RunnablePassthrough(), "history": lambda x: history_text} 
                | ChatPromptTemplate.from_template(template) 
                | llm 
                | StrOutputParser()
            )
        else:
            template = """You are an AI assistant with access to the user's documents. 
The context below contains relevant excerpts from the documents along with their source filenames.
Answer the question based on the context provided and the conversation history.
If the user asks what files or documents you have access to, list the unique source filenames from the context.
If you cannot find the answer in the context, say so clearly.

Conversation History:
{history}

Document Context:
{context}

User Question: {question}

Provide a helpful response based on the documents."""
            
            def get_context(query):
                docs = retriever.invoke(query) if hasattr(retriever, 'invoke') else retriever.get_relevant_documents(query)
                return format_docs(docs)
            
            chain = (
                {"context": lambda x: get_context(x), "question": RunnablePassthrough(), "history": lambda x: history_text} 
                | ChatPromptTemplate.from_template(template) 
                | llm 
                | StrOutputParser()
            )
        
        def generate():
            full_response = ""
            try:
                for chunk in chain.stream(query):
                    full_response += chunk
                    yield chunk
                
                # Save to database after successful completion
                add_message(session_id, 'user', query)
                add_message(session_id, 'assistant', full_response)
            except Exception as e:
                error_msg = f"\n\n[Error: {str(e)}]"
                yield error_msg

        return Response(generate(), mimetype='text/plain')
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/ocr", methods=["POST"])
def ocr():
    """Extract text from uploaded images using OCR."""
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
    
    image_file = request.files["image"]
    if image_file.filename == "":
        return jsonify({"error": "No selected file"}), 400
        
    try:
        image = Image.open(image_file)
        text = pytesseract.image_to_string(image)
        if not text.strip():
            return jsonify({"text": "", "warning": "No text detected in image"})
        return jsonify({"text": text})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/")
def index():
    """Render the main application page."""
    config = load_config()
    message = request.args.get("message")
    status = request.args.get("status")
    
    session_id = get_current_session()
    chat_history = get_messages(session_id)
    sessions = get_all_sessions(limit=20)
    
    # Convert to format expected by template
    formatted_history = [(msg['role'].capitalize(), msg['content']) for msg in chat_history]
    
    return render_template(
        "index.html", 
        config=config, 
        message=message, 
        status=status, 
        chat_history=formatted_history,
        sessions=sessions,
        current_session_id=session_id,
        indexed_files=get_indexed_files(),
        available_models=config.get('available_models', DEFAULT_CONFIG['available_models'])
    )


@app.route("/set_model", methods=["POST"])
def set_model():
    """Change the active LLM model."""
    model = request.form.get("model")
    if not model:
        return redirect(url_for("index", message="No model specified", status="error"))
    
    config = load_config()
    
    # Check if model is available in Ollama
    model_check = check_model_available(model, config.get("ollama_host", "http://localhost:11434"))
    if not model_check["available"]:
        return redirect(url_for("index", message=f"Model not available: {model_check['error']}", status="error"))
    
    update_config({"model": model})
    
    msg = f"Switched to {model}"
    if "gemma" in model.lower():
        msg = "Switched to Gemma"
    elif "qwen" in model.lower():
        msg = "Switched to Qwen"
    elif "llama" in model.lower():
        msg = "Switched to Llama"
    elif "phi" in model.lower():
        msg = "Switched to Phi"
        
    return redirect(url_for("index", message=msg, status="success"))


@app.route("/set_mode", methods=["POST"])
def set_mode():
    """Toggle between CLI and browser chat modes."""
    data = request.json
    mode = data.get("mode")
    
    if mode not in ["cli", "browser"]:
        return jsonify({"error": "Invalid mode"}), 400
    
    update_config({"mode": mode})
    return jsonify({"status": "success", "mode": mode})


@app.route("/upload", methods=["POST"])
def upload():
    """Upload and ingest documents into the knowledge base."""
    if "files" not in request.files:
        return redirect(url_for("index", message="No file part", status="error"))
    
    files = request.files.getlist("files")
    paths = []
    
    for file in files:
        if file.filename == "": 
            continue
        path = os.path.join(UPLOAD_DIR, file.filename)
        file.save(path)
        paths.append(path)
    
    if paths:
        success, msg = ingest_files(paths)
        status = "success" if success else "error"
        return redirect(url_for("index", message=msg, status=status))
    
    return redirect(url_for("index", message="No files selected", status="error"))


# ============== NEW API ENDPOINTS ==============

@app.route("/api/health", methods=["GET"])
def api_health():
    """Get system health status including Ollama and model availability."""
    try:
        status = get_system_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/settings", methods=["GET"])
def get_settings():
    """Get all current settings."""
    config = load_config()
    return jsonify(config)


@app.route("/api/settings", methods=["POST"])
def update_settings():
    """Update settings."""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validate the config
        current = load_config()
        current.update(data)
        
        is_valid, errors = validate_config(current)
        if not is_valid:
            return jsonify({"error": "Validation failed", "details": errors}), 400
        
        update_config(data)
        return jsonify({"status": "success", "config": load_config()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/settings/reset", methods=["POST"])
def reset_settings():
    """Reset settings to defaults."""
    from config_manager import reset_config
    config = reset_config()
    return jsonify({"status": "success", "config": config})


@app.route("/api/sessions", methods=["GET"])
def list_sessions():
    """Get all chat sessions."""
    sessions = get_all_sessions()
    return jsonify({"sessions": sessions, "current": get_current_session()})


@app.route("/api/sessions", methods=["POST"])
def new_session():
    """Create a new chat session."""
    global CURRENT_SESSION_ID
    data = request.json or {}
    name = data.get("name")
    
    config = load_config()
    session_id = create_session(name=name, model_used=config.get("model"))
    CURRENT_SESSION_ID = session_id
    
    return jsonify({"status": "success", "session_id": session_id})


@app.route("/api/sessions/<int:session_id>", methods=["GET"])
def get_session_messages(session_id):
    """Get all messages for a specific session."""
    messages = get_messages(session_id)
    return jsonify({"session_id": session_id, "messages": messages})


@app.route("/api/sessions/<int:session_id>/switch", methods=["POST"])
def switch_session(session_id):
    """Switch to a different chat session."""
    global CURRENT_SESSION_ID
    from database import get_session
    
    session = get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    
    CURRENT_SESSION_ID = session_id
    messages = get_messages(session_id)
    return jsonify({"status": "success", "session_id": session_id, "messages": messages})


@app.route("/api/sessions/<int:session_id>", methods=["DELETE"])
def delete_chat_session(session_id):
    """Delete a chat session."""
    global CURRENT_SESSION_ID
    
    if delete_session(session_id):
        if CURRENT_SESSION_ID == session_id:
            CURRENT_SESSION_ID = get_or_create_default_session()
        return jsonify({"status": "success"})
    return jsonify({"error": "Session not found"}), 404


@app.route("/api/sessions/<int:session_id>/clear", methods=["POST"])
def clear_session(session_id):
    """Clear all messages in a session."""
    count = clear_session_messages(session_id)
    return jsonify({"status": "success", "cleared": count})


@app.route("/api/sessions/<int:session_id>/rename", methods=["POST"])
def rename_chat_session(session_id):
    """Rename a chat session."""
    data = request.json
    new_name = data.get("name")
    
    if not new_name:
        return jsonify({"error": "Name required"}), 400
    
    if rename_session(session_id, new_name):
        return jsonify({"status": "success"})


@app.route("/api/sessions/<int:session_id>/export", methods=["GET"])
def export_session(session_id):
    """Export chat session as a downloadable file."""
    format_type = request.args.get("format", "txt")
    
    # Get session details
    sessions = get_all_sessions()
    session_name = "Chat"
    for s in sessions:
        if s["id"] == session_id:
            session_name = s["name"]
            break
            
    # Clean filename
    safe_name = "".join([c for c in session_name if c.isalnum() or c in (' ', '-', '_')]).strip()
    safe_name = safe_name.replace(" ", "_")
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{safe_name}_{date_str}.{format_type}"
    
    # Get messages
    messages = get_messages(session_id)
    
    # Generate content
    content = ""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if format_type == "md":
        content = f"# {session_name}\n\nExported on {timestamp}\n\n---\n\n"
        for msg in messages:
            role = "**You**" if msg["role"] == "user" else "**Assistant**"
            content += f"{role}:\n\n{msg['content']}\n\n---\n\n"
        mimetype = "text/markdown"
    else:
        content = f"{session_name}\nExported on {timestamp}\n{'='*50}\n\n"
        for msg in messages:
            role = "You" if msg["role"] == "user" else "Assistant"
            content += f"[{role}]:\n{msg['content']}\n\n{'-'*40}\n\n"
        mimetype = "text/plain"
        
    # Return as downloadable file
    from werkzeug.wrappers import Response
    return Response(
        content,
        mimetype=mimetype,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
    return jsonify({"error": "Session not found"}), 404


@app.route("/api/index/stats", methods=["GET"])
def index_stats():
    """Get statistics about the vector index."""
    stats = get_index_stats()
    return jsonify(stats)


@app.route("/api/stats", methods=["GET"])
def app_stats():
    """Get aggregated application statistics for the dashboard."""
    try:
        # Get index stats
        idx_stats = get_index_stats()
        
        # Get session stats
        sessions = get_all_sessions()
        total_sessions = len(sessions)
        
        # Calculate total messages
        total_messages = 0
        for s in sessions:
            msgs = get_messages(s['id'])
            total_messages += len(msgs)
            
        # Get config for model info
        config = load_config()
        
        return jsonify({
            "total_documents": idx_stats.get("total_files", 0),
            "total_chunks": idx_stats.get("total_chunks", 0),
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "current_model": config.get("model", "Unknown"),
            "hybrid_search": config.get("use_hybrid_search", False)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/index/clear", methods=["POST"])
def clear_vector_index():
    """Clear all indexed documents."""
    success, msg = clear_index()
    if success:
        return jsonify({"status": "success", "message": msg})
    return jsonify({"error": msg}), 500


@app.route("/api/index/files", methods=["GET"])
def list_indexed_files():
    """Get list of indexed files."""
    files = get_indexed_files()
    return jsonify({"files": files, "count": len(files)})


# ============== FILE MANAGEMENT API ==============

@app.route("/api/files", methods=["GET"])
def list_uploaded_files():
    """List all uploaded files with metadata."""
    files = []
    
    if os.path.exists(UPLOAD_DIR):
        for filename in os.listdir(UPLOAD_DIR):
            filepath = os.path.join(UPLOAD_DIR, filename)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                ext = os.path.splitext(filename)[1].lower()
                
                # Determine file type icon
                file_type = "document"
                if ext == ".pdf":
                    file_type = "pdf"
                elif ext in [".doc", ".docx"]:
                    file_type = "word"
                elif ext in [".xls", ".xlsx"]:
                    file_type = "excel"
                elif ext in [".ppt", ".pptx"]:
                    file_type = "powerpoint"
                elif ext in [".txt", ".md"]:
                    file_type = "text"
                elif ext == ".csv":
                    file_type = "csv"
                elif ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp"]:
                    file_type = "image"
                
                files.append({
                    "name": filename,
                    "path": filepath,
                    "size": stat.st_size,
                    "size_formatted": format_file_size(stat.st_size),
                    "modified": stat.st_mtime,
                    "extension": ext,
                    "type": file_type,
                    "indexed": filename in get_indexed_files()
                })
    
    # Sort by modified time (newest first)
    files.sort(key=lambda x: x["modified"], reverse=True)
    return jsonify({"files": files, "count": len(files)})


def format_file_size(size_bytes):
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


@app.route("/api/files/upload", methods=["POST"])
def api_upload_files():
    """Upload files via API (returns JSON instead of redirect)."""
    if "files" not in request.files:
        return jsonify({"error": "No files provided"}), 400
    
    files = request.files.getlist("files")
    uploaded = []
    failed = []
    
    for file in files:
        if file.filename == "":
            continue
        
        try:
            # Secure the filename
            filename = file.filename
            filepath = os.path.join(UPLOAD_DIR, filename)
            
            # Handle duplicate filenames
            counter = 1
            base_name, ext = os.path.splitext(filename)
            while os.path.exists(filepath):
                filename = f"{base_name}_{counter}{ext}"
                filepath = os.path.join(UPLOAD_DIR, filename)
                counter += 1
            
            file.save(filepath)
            uploaded.append({
                "name": filename,
                "path": filepath,
                "size": os.path.getsize(filepath),
                "size_formatted": format_file_size(os.path.getsize(filepath))
            })
        except Exception as e:
            failed.append({"name": file.filename, "error": str(e)})
    
    return jsonify({
        "status": "success" if uploaded else "error",
        "uploaded": uploaded,
        "failed": failed,
        "message": f"Uploaded {len(uploaded)} file(s)" + (f", {len(failed)} failed" if failed else "")
    })


@app.route("/api/files/<path:filename>", methods=["DELETE"])
def delete_file(filename):
    """Delete a specific file."""
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
    
    try:
        os.remove(filepath)
        return jsonify({"status": "success", "message": f"Deleted {filename}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/files/delete-multiple", methods=["POST"])
def delete_multiple_files():
    """Delete multiple files at once."""
    data = request.json
    filenames = data.get("files", [])
    
    if not filenames:
        return jsonify({"error": "No files specified"}), 400
    
    deleted = []
    failed = []
    
    for filename in filenames:
        filepath = os.path.join(UPLOAD_DIR, filename)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                deleted.append(filename)
            else:
                failed.append({"name": filename, "error": "File not found"})
        except Exception as e:
            failed.append({"name": filename, "error": str(e)})
    
    return jsonify({
        "status": "success" if deleted else "error",
        "deleted": deleted,
        "failed": failed,
        "message": f"Deleted {len(deleted)} file(s)" + (f", {len(failed)} failed" if failed else "")
    })


@app.route("/api/files/ingest", methods=["POST"])
def ingest_selected_files():
    """Ingest specific files into the vector store."""
    data = request.json
    filenames = data.get("files", [])
    
    if not filenames:
        return jsonify({"error": "No files specified"}), 400
    
    paths = []
    for filename in filenames:
        filepath = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(filepath):
            paths.append(filepath)
    
    if not paths:
        return jsonify({"error": "No valid files found"}), 400
    
    success, msg = ingest_files(paths)
    
    if success:
        return jsonify({"status": "success", "message": msg})
    return jsonify({"error": msg}), 500


@app.route("/api/files/<path:filename>/ingest", methods=["POST"])
def ingest_single_file(filename):
    """Ingest a single file into the vector store."""
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
    
    success, msg = ingest_files([filepath])
    
    if success:
        return jsonify({"status": "success", "message": msg})
    return jsonify({"error": msg}), 500


@app.route("/api/files/preview/<path:filename>")
def preview_file(filename):
    """Get a preview of a file's content."""
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
    
    ext = os.path.splitext(filename)[1].lower()
    
    try:
        if ext in [".txt", ".md", ".csv"]:
            # Read text files directly
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(5000)  # First 5000 chars
                if len(content) == 5000:
                    content += "\n\n... (truncated)"
            return jsonify({"type": "text", "content": content})
        
        elif ext == ".pdf":
            # Get first page text from PDF
            try:
                from langchain_community.document_loaders import PyPDFLoader
                loader = PyPDFLoader(filepath)
                docs = loader.load()
                if docs:
                    content = docs[0].page_content[:3000]
                    if len(docs) > 1:
                        content += f"\n\n... ({len(docs)} pages total)"
                    return jsonify({"type": "text", "content": content, "pages": len(docs)})
            except:
                pass
            return jsonify({"type": "info", "content": "PDF preview not available"})
        
        elif ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp"]:
            # Return image info
            from PIL import Image as PILImage
            img = PILImage.open(filepath)
            return jsonify({
                "type": "image",
                "width": img.width,
                "height": img.height,
                "format": img.format,
                "url": f"/uploaded_files/{filename}"
            })
        
        else:
            return jsonify({
                "type": "info", 
                "content": f"Preview not available for {ext} files.\nFile size: {format_file_size(os.path.getsize(filepath))}"
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Serve uploaded files for preview
from flask import send_from_directory

@app.route("/uploaded_files/<path:filename>")
def serve_uploaded_file(filename):
    """Serve uploaded files for preview."""
    return send_from_directory(UPLOAD_DIR, filename)


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    if request.path.startswith('/api/'):
        return jsonify({"error": "Endpoint not found"}), 404
    return render_template("index.html", config=load_config(), message="Page not found", status="error")


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    traceback.print_exc()
    if request.path.startswith('/api/'):
        return jsonify({"error": "Internal server error"}), 500
    return render_template("index.html", config=load_config(), message="Server error occurred", status="error")


if __name__ == "__main__":
    # Initialize the database
    from database import init_db
    init_db()
    
    config = load_config()
    print(f"\n{'='*50}")
    print("RAG Agent Web Server Starting...")
    print(f"Model: {config.get('model', 'gemma3:270m')}")
    print(f"Hybrid Search: {'Enabled' if config.get('use_hybrid_search') else 'Disabled'}")
    print(f"{'='*50}\n")
    
    app.run(port=8501, debug=True)
