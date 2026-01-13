"""
Enhanced Flask Application with Persistent Chat Memory, Health Checks, and Improved Error Handling.
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify, Response, send_from_directory
import os
import re
import sys
import subprocess
import shutil
import time
import json
import traceback
import base64
from datetime import datetime
from flask_cors import CORS
from backend import ingest_files, get_rag_chain, clear_index, get_indexed_files, get_index_stats, load_document_content, deep_search
from config_manager import load_config, save_config, update_config, DEFAULT_CONFIG, validate_config
from database import (
    get_or_create_default_session, create_session, get_all_sessions,
    add_message, get_messages, format_history_for_prompt, 
    delete_session, rename_session, clear_session_messages,
    toggle_pin_session, get_pinned_sessions,
    create_prompt, get_all_prompts, delete_prompt, search_chat_data,
    get_total_message_count,
    get_all_file_tags, set_file_tags, get_file_tags
)

from health_check import check_ollama_health, check_model_available, get_system_status
from models_manager import list_models, delete_model, pull_model_stream
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_ollama import ChatOllama
from PIL import Image
import pytesseract
from concurrent.futures import ThreadPoolExecutor
import uuid
import time
from tools import TOOL_REGISTRY, TOOL_DEFINITIONS
from security import analyze_tool_call, DESTRUCTIVE_ACTIONS, is_safe_path
from logging_config import setup_logging

# Initialize Logger
logger = setup_logging()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
APP_VERSION = "2.0.0.0"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploaded_files")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Async Background Processing
executor = ThreadPoolExecutor(max_workers=1)
TASKS = {} # {task_id: {"status": "processing"|"completed"|"failed", "result": ...}}

def run_ingest_task(task_id, file_paths):
    """Background task wrapper for ingestion."""
    TASKS[task_id] = {"status": "processing", "started_at": time.time()}
    try:
        from backend import ingest_files 
        result = ingest_files(file_paths)
        TASKS[task_id]["status"] = "completed"
        TASKS[task_id]["result"] = result
        TASKS[task_id]["completed_at"] = time.time()
    except Exception as e:
        TASKS[task_id]["status"] = "failed"
        TASKS[task_id]["error"] = str(e)
        TASKS[task_id]["completed_at"] = time.time()

# Current active session (fallback only - refrain from updating globally)
CURRENT_SESSION_ID = None

# Shared memory for browser content (Chrome Extension sync)
# ideally this should be user-specific, but keeping simple for now
# Shared memory for browser content (Chrome Extension sync)
# Now keyed by session_id to prevent leaks
BROWSER_SESSIONS = {}

# Pre-compile regex patterns for greeting detection (performance optimization)
GREETING_PATTERNS = [
    re.compile(pattern) for pattern in [
        r'\bhello\b', r'\bhi\b', r'\bhey\b', r'\bgood morning\b', r'\bgood evening\b',
        r'\bgood afternoon\b', r'\bhow are you\b', r"\bwhat'?s up\b", r'\bthanks\b',
        r'\bthank you\b', r'\bbye\b', r'\bgoodbye\b', r'\bwho are you\b',
        r'\bwhat can you do\b', r'\bhelp me\b'
    ]
]



def get_current_session():
    """Get or create the current chat session (Fallback if no ID provided)."""
    global CURRENT_SESSION_ID
    if CURRENT_SESSION_ID is None:
        CURRENT_SESSION_ID = get_or_create_default_session()
    return CURRENT_SESSION_ID

# ... (lines 55-585 preserved) ...

@app.route("/api/files", methods=["GET"])
def list_files():
    """List uploaded files."""
    files = []
    if os.path.exists(UPLOAD_DIR):
        for f in os.listdir(UPLOAD_DIR):
            path = os.path.join(UPLOAD_DIR, f)
            if os.path.isfile(path):
                try:
                    stats = os.stat(path)
                    files.append({
                        "name": f,
                        "size": stats.st_size,
                        "created": datetime.fromtimestamp(stats.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                         "modified": datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    })
                except Exception:
                    continue
    
    # Get tags for all files
    all_tags = get_all_file_tags()
    
    # Merge tags into file list
    for file in files:
        file['tags'] = all_tags.get(file['name'], [])
    
    # Sort by modified date descending (newest first)
    files.sort(key=lambda x: x['modified'], reverse=True)
    
    return jsonify({"files": files})


@app.route("/api/files/<path:filename>/tags", methods=["POST", "DELETE"])
def update_file_tags(filename):
    """Update tags for a file."""
    # SECURITY: Check path
    if not is_safe_path(filename):
        return jsonify({"error": "Invalid filename"}), 400
        
    if request.method == "POST":
        data = request.json
        tags = data.get("tags", [])
        if not isinstance(tags, list):
            return jsonify({"error": "Tags must be a list"}), 400
            
        success = set_file_tags(filename, tags)
        return jsonify({"status": "success" if success else "error"})
        
    return jsonify({"error": "Method not allowed"}), 405


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
            
        # SECURITY: Check path
        if not is_safe_path(file.filename):
             return redirect(url_for("index", message=f"Invalid filename: {file.filename}", status="error"))
             
        path = os.path.join(UPLOAD_DIR, file.filename)
        file.save(path)
        paths.append(path)
    
    if paths:
        # Offload to background thread
        task_id = str(uuid.uuid4())
        executor.submit(run_ingest_task, task_id, paths)
        
        msg = f"Ingestion started in background. (Task ID: {task_id[:8]})"
        return redirect(url_for("index", message=msg, status="info"))
    
    return redirect(url_for("index", message="No files selected", status="error"))

# ... (lines 615-690 preserved) ...

@app.route("/api/sessions", methods=["POST"])
def new_session():
    """Create a new chat session."""
    # Removed global state update
    data = request.json or {}
    name = data.get("name")
    
    config = load_config()
    session_id = create_session(name=name, model_used=config.get("model"))
    
    return jsonify({"status": "success", "session_id": session_id})


@app.route("/api/search", methods=["GET"])
def api_search():
    """Search chat sessions, messages, and files."""
    from database import search_chat_data
    
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Search query required", "sessions": [], "messages": [], "files": []}), 400
    
    results = search_chat_data(query)
    
    # Also search files
    matching_files = []
    try:
        for filename in os.listdir(UPLOAD_DIR):
            if query.lower() in filename.lower():
                matching_files.append(filename)
    except Exception:
        pass
    
    return jsonify({
        "query": query,
        "sessions": results.get("sessions", []),
        "messages": results.get("messages", []),
        "files": matching_files,
        "total": len(results.get("sessions", [])) + len(results.get("messages", [])) + len(matching_files)
    })


@app.route("/api/sessions/<int:session_id>", methods=["GET"])
def get_session_messages(session_id):
    """Get messages for a specific session (optional polling with after_id)."""
    after_id = request.args.get('after_id', type=int)
    
    if after_id is not None:
        from database import get_new_messages
        messages = get_new_messages(session_id, after_id)
    else:
        messages = get_messages(session_id)
        
    return jsonify({"session_id": session_id, "messages": messages})


@app.route("/api/sessions/<int:session_id>/switch", methods=["POST"])
def switch_session(session_id):
    """Switch to a different chat session."""
    # Removed global state update
    from database import get_session
    
    session = get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    
    messages = get_messages(session_id)
    return jsonify({"status": "success", "session_id": session_id, "messages": messages})


@app.route("/api/sessions/<int:session_id>/export", methods=["GET"])
def export_session(session_id):
    """Export a chat session as JSON or Markdown."""
    from database import get_session
    
    export_format = request.args.get("format", "json").lower()
    
    session = get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    
    messages = get_messages(session_id)
    
    if export_format == "md" or export_format == "markdown":
        # Markdown format
        session_name = session.get('name', session.get('title', 'Chat Session'))
        md_content = f"# {session_name}\n\n"
        md_content += f"*Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n---\n\n"
        
        for msg in messages:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            timestamp = msg.get("created_at", "")
            md_content += f"### {role}\n*{timestamp}*\n\n{content}\n\n---\n\n"
        
        response = Response(md_content, mimetype="text/markdown")
        filename = f"chat_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        return response
    
    else:
        # JSON format (default)
        export_data = {
            "session": session,
            "messages": messages,
            "exported_at": datetime.now().isoformat(),
            "version": APP_VERSION
        }
        response = jsonify(export_data)
        filename = f"chat_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        return response


@app.route("/api/sessions/<int:session_id>/pin", methods=["POST"])
def toggle_session_pin_route(session_id):
    """Toggle pin status for a session."""
    from database import toggle_chat_pin
    new_status = toggle_chat_pin(session_id)
    if new_status is None:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({"status": "success", "is_pinned": new_status})


@app.route("/api/sessions/<int:session_id>", methods=["DELETE"])
def delete_chat_session(session_id):
    """Delete a chat session."""
    # Removed global state update logic (client handles redirect)
    
    if delete_session(session_id):
        return jsonify({"status": "success"})
    return jsonify({"error": "Session not found"}), 404


@app.route("/api/sessions/bulk_delete", methods=["POST"])
def bulk_delete_sessions():
    """Delete multiple chat sessions."""
    # Removed global state logic
    data = request.json
    session_ids = data.get("session_ids", [])
    
    if not session_ids:
        return jsonify({"error": "No session IDs provided"}), 400
        
    deleted_count = 0
    for session_id in session_ids:
        if delete_session(session_id):
            deleted_count += 1
                
    return jsonify({"status": "success", "deleted_count": deleted_count})

# ... (lines 770-970 preserved) ...

@app.route("/api/documents/<path:filename>", methods=["DELETE"])
def delete_document(filename):
    """Delete an indexed document."""
    # SECURITY: Check path
    if not is_safe_path(filename):
        return jsonify({"error": "Invalid filename"}), 400
        
    # Delete the physical file if it exists in uploads
    filepath = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            # Note: File will still be in FAISS index until index is rebuilt
            return jsonify({"status": "success", "message": f"Deleted {filename}. Rebuild index to fully remove."})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    return jsonify({"error": "File not found"}), 404

# ... (lines 990-1048 preserved) ...

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
            
            # SECURITY: Check path
            if not is_safe_path(filename):
                failed.append({"name": filename, "error": "Invalid filename (Path traversal detected)"})
                continue
            
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
    # SECURITY: Check path
    if not is_safe_path(filename):
        return jsonify({"error": "Invalid filename"}), 400

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
        # SECURITY: Check path
        if not is_safe_path(filename):
            failed.append({"name": filename, "error": "Invalid filename"})
            continue
            
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
        # SECURITY: Check path
        if not is_safe_path(filename):
             continue 
             
        filepath = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(filepath):
            paths.append(filepath)
    
    if not paths:
        return jsonify({"error": "No valid files found"}), 400
    
    # Offload to background thread
    task_id = str(uuid.uuid4())
    executor.submit(run_ingest_task, task_id, paths)
    
    return jsonify({
        "status": "processing", 
        "task_id": task_id,
        "message": "Ingestion started in background."
    }), 202


@app.route("/api/files/<path:filename>/ingest", methods=["POST"])
def ingest_single_file(filename):
    """Ingest a single file into the vector store."""
    filepath = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
        
    result = ingest_files([filepath])
    
    if result["success"] and result["processed_count"] > 0:
        return jsonify(result)
    
    return jsonify(result), 400


@app.route("/api/files/preview/<path:filename>")
def preview_file(filename):
    """Get a preview of a file's content."""
    # SECURITY: Check path
    if not is_safe_path(filename):
        return jsonify({"error": "Invalid filename"}), 400

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
                "content": f"Preview not available for {ext} files.\nFile size: {os.path.getsize(filepath)} bytes"
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def format_docs(docs):
    """Format retrieved documents with source information."""
    formatted = []
    for doc in docs:
        source = doc.metadata.get('source', 'Unknown')
        content = doc.page_content
        formatted.append(f"Source: {source}\nContent: {content}")
    return "\n\n".join(formatted)


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint for monitoring."""
    config = load_config()
    ollama_host = config.get("ollama_host", "http://localhost:11434")
    ollama_status = check_ollama_health(ollama_host)
    
    return jsonify({
        "status": "healthy",
        "ollama": {
            "available": ollama_status["available"],
            "error": ollama_status.get("error")
        },
        "model": config.get("model", "unknown"),
        "mode": config.get("mode", "cli")
    })


@app.route("/chat", methods=["POST"])
def chat():
    """Handle chat messages with persistent history and streaming responses."""
    try:
        data = request.json
        print(f"[DEBUG] /chat request received. Files: {len(data.get('files', []))}", flush=True)
        
        query = data.get("message", "").strip()
        files = data.get("files", [])  # Unified: {type, name, data, addToRag}
        
        # Separate files by type
        images = [f for f in files if f.get("type") == "image"]
        documents = [f for f in files if f.get("type") == "document"]
        

        
        if not query and not files:
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
        
        # === DOCUMENT PROCESSING (Background - uses embedding model) ===
        docs_ingested = False
        temp_doc_content = []  # For docs not added to RAG (temp analysis)
        
        if documents:
            print(f"[DEBUG] Processing {len(documents)} documents", flush=True)
            rag_paths = []  # Docs to ingest into RAG
            
            for doc in documents:
                try:
                    doc_name = doc.get("name", "uploaded_doc.txt")
                    doc_data = doc.get("data", "")
                    add_to_rag = doc.get("addToRag", False)
                    
                    # Extract base64 data (remove header if present)
                    if "," in doc_data:
                        doc_data = doc_data.split(",")[1]
                    
                    # Decode and save
                    file_bytes = base64.b64decode(doc_data)
                    file_path = os.path.join(UPLOAD_DIR, doc_name)
                    with open(file_path, "wb") as f:
                        f.write(file_bytes)
                    
                    if add_to_rag:
                        rag_paths.append(file_path)
                    else:
                        # For temp analysis, use same loaders as RAG system
                        content = load_document_content(file_path)
                        print(f"[DEBUG] Loaded temp doc '{doc_name}': {len(content)} chars", flush=True)
                        temp_doc_content.append(f"[Document: {doc_name}]\n{content[:8000]}")
                            
                except Exception as e:
                    print(f"Error processing document {doc.get('name')}: {e}")
            
            # Ingest RAG documents with embedding model
            if rag_paths:
                success, msg = ingest_files(rag_paths)
                if success:
                    docs_ingested = True
                    print(f"Chat documents ingested to RAG: {msg}")
                else:
                    print(f"Failed to ingest chat documents: {msg}")
        
        retriever, llm = get_rag_chain(model_name)
        
        # === VISION PATH (Two-Stage Pipeline) ===
        # 1. Internal Vision AI extracts context (Description)
        # 2. Description is fed to Foreground LLM as context
        vision_context = ""
        if images:
            try:
                print("[DEBUG] Processing images with Vision AI (moondream)...", flush=True)
                # Clean Base64 strings
                cleaned_images = []
                for img_file in images:
                    try:
                        img_data = img_file.get("data", "")
                        if "," in img_data:
                            img_data = img_data.split(",")[1]
                        
                        # Save to disk for serving
                        raw_name = img_file.get("name", f"image_{int(time.time())}.png")
                        img_name = os.path.basename(raw_name)  # Simple sanitization
                        img_path = os.path.join(UPLOAD_DIR, img_name)
                        
                        with open(img_path, "wb") as f:
                            f.write(base64.b64decode(img_data))
                        
                        cleaned_images.append(img_data)
                    except Exception as e:
                        print(f"[ERROR] Failed to save image {img_file.get('name')}: {e}", flush=True)
                        continue
                
                # Call Vision Model (moondream)
                # We use a dedicated instance for vision to ensure capacity
                vision_llm = ChatOllama(model="moondream", base_url=config.get("ollama_host", "http://localhost:11434"))
                
                # Construct Multimodal Message (Modern LangChain/Ollama Format)
                content_parts = [
                    {"type": "text", "text": "Describe this image. List prominent colors, objects, and any text visible."}
                ]
                
                for img_file in images:
                    # Use full data URL (with header) for LangChain
                    # If data is raw base64 (no header), ad-hoc allow it, but frontend sends Data URL.
                    img_data_full = img_file.get("data", "")
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {"url": img_data_full}
                    })

                vision_messages = [
                    HumanMessage(content=content_parts)
                ]
                
                # Get Description
                vision_response = vision_llm.invoke(vision_messages)
                description = vision_response.content
                print(f"[DEBUG] Vision AI FULL Description: '{description}'", flush=True)
                
                # Detect if moondream refused to process the image
                refusal_patterns = [
                    "i don't have access",
                    "i can't view",
                    "i'm sorry, but i can't",
                    "i cannot assist with that",
                    "i'm unable to view",
                    "i'm unable to see",
                    "unfortunately, i don't have access"
                ]
                description_lower = description.lower().strip()
                
                # Check for empty or very short responses (also a sign of refusal)
                is_empty_or_short = len(description.strip()) < 10
                is_refusal = any(pattern in description_lower for pattern in refusal_patterns) or is_empty_or_short
                
                print(f"[DEBUG] Refusal detected: {is_refusal} (empty={is_empty_or_short}, len={len(description)})", flush=True)
                
                if is_refusal:
                    # moondream refused - provide helpful feedback
                    vision_context = f"\n\n[VISION SYSTEM LIMITATION]\nThe vision model (moondream) was unable to process the uploaded image. This typically happens with:\n- Large images (>1MB)\n- High-resolution photos with complex scenes\n- Images with heavy compression artifacts\n\nSUGGESTIONS:\n1. Try resizing/compressing the image before upload\n2. Use a more capable vision model like 'llava:latest' or 'minicpm-v' (available via Settings > Model)\n3. Simplify the image (crop to focus on specific area)\n\nFor now, respond to the user's query acknowledging you cannot analyze this specific image, and ask them to try the suggestions above.\n"
                else:
                    vision_context = f"\n\n[HIDDEN CONTEXT FROM VISION AI]\nThe user has attached images. Here is the internal description of those images:\n{description}\n(The user cannot see this description directly. Use it to answer their questions about the image.)\n"
                
            except Exception as e:
                print(f"[ERROR] Vision processing failed: {e}", flush=True)
                vision_context = f"\n\n[SYSTEM ERROR] Failed to process attached images: {str(e)}"

        # === STANDARD TEXT/RAG PATH (Now includes Vision Context) ===
        
        # Get conversation history from database
        history_text = format_history_for_prompt(session_id, max_history)
        
        # Inject browser context if in browser mode
        # Use str(session_id) to ensure key consistency
        session_key = str(session_id)
        browser_context_data = BROWSER_SESSIONS.get(session_key, {})
        
        if config.get("mode") == "browser" and browser_context_data.get("content"):
            browser_content = browser_context_data.get("content", "")[:4000]  # Truncate to avoid overflow
            browser_url = browser_context_data.get("url", "")
            query = f"""CONTEXT FROM ACTIVE BROWSER TAB ({browser_url}):
{browser_content}

USER QUERY:
{query}"""
        
        # Intent detection: Check if query needs document context
        query_lower = query.lower().strip()
        # Use pre-compiled regex patterns for efficiency
        is_greeting = any(pattern.search(query_lower) for pattern in GREETING_PATTERNS)
        is_greeting_or_meta = is_greeting and len(query_lower) < 50
        
        # Document-specific keywords - triggers RAG only when user explicitly mentions documents
        doc_keywords = ['document', 'file', 'uploaded', 'indexed', 'my files', 'in the context',
                        'according to', 'based on', 'from the', 'in my', 'search my', 'find in',
                        'what does the document say', 'summary of', 'readme', 'pdf', 'txt', 'csv']
        needs_rag = (any(keyword in query_lower for keyword in doc_keywords) or docs_ingested) and not is_greeting_or_meta
        
        # ==========================================
        # AGENTIC LOOP IMPLEMENTATION (Phase 1.2)
        # ==========================================
        
        # Models that act as pure chat/RAG only (no agentic tools)
        NON_TOOL_MODELS = ["gemma2:2b", "moondream", "llama3.2:1b", "qwen2.5:0.5b", "gemma3:270m"]

        # 1. Prepare Tools
        # Skip tool binding for:
        # - Greetings/meta queries (don't need tools)
        # - Temp doc analysis (doc content in prompt, no tools needed)
        # - Models that don't support tools (prevents crash)
        skip_tools = is_greeting_or_meta or bool(temp_doc_content) or (model_name in NON_TOOL_MODELS)
        llm_with_tools = llm.bind_tools(TOOL_DEFINITIONS) if not skip_tools else llm

        # 2. Define the System Prompt
        if is_greeting_or_meta:
             system_prompt = """You are a friendly AI assistant called Local RAG Agent.
Respond directly to greetings and general questions warmly."""
             if vision_context:
                 system_prompt += vision_context
        else:
            # === RAG & AGENT PROMPTS ===
            if skip_tools:
                # Simplified prompt for models that cannot use tools (Prevents hallucinations)
                system_prompt = """You are a helpful Assistant with access to the user's local files.
I have provided the list of available files below in your context.

GUIDELINES:
1. **Context First**: Answer based on the provided file content and list.
2. **Capabilities**: You can answer questions about the files I list.
3. **No Hallucinations**: Do not claim to use tools like `list_files` or `ingest`. Just say what you see.
4. **General**: For generic questions, answer normally.

Conversation History:
{history}
"""
            else:
                system_prompt = """You are an Agentic Assistant with access to the user's local files.
You can read (ingest), delete, and list files.

GUIDELINES:
1. **Context First**: If the user asks about a file, try to find it in your context or valid file list.
2. **Tools**: Use `list_files` to see what's available. Use `ingest_document` to memorize a file.
3. **Safety**: If asked to delete something, use `delete_document` (I will ask for approval).
4. **General**: For generic questions, answer normally without tools.
5. **No Hallucinations**: Do not invent file content.

Conversation History:
{history}
"""
            # Format history immediately to avoid issues with braces in appended content later
            system_prompt = system_prompt.format(history="")

            # Add RAG Context if available
            if retriever:
                 try:
                    if use_deep_search:
                         print(f"PERFORMING DEEP SEARCH for: {query}")
                         docs = deep_search(query, retriever, llm)
                    else:
                         docs = retriever.invoke(query)
                         
                    if docs:
                        context_str = format_docs(docs)
                        system_prompt += f"\n\nRELEVANT DOCUMENT CONTEXT:\n{context_str}\n"
                 except Exception as e:
                     print(f"Retrieval warning: {e}")
            
            # Add temp document content (for documents not added to RAG)
            if temp_doc_content:
                temp_content_str = "\n\n".join(temp_doc_content)
                system_prompt += f"\n\nUPLOADED DOCUMENT CONTENT (for this session only):\n{temp_content_str}\n"
                print(f"[DEBUG] Added temp_doc_content to prompt: {len(temp_content_str)} chars", flush=True)

            # Inject File Catalog (so model knows what it has without tools)
            try:
                catalog_paths = get_indexed_files() # Returns list of source paths
                print(f"[DEBUG] get_indexed_files returned: {len(catalog_paths)} files", flush=True)
                if catalog_paths:
                    # Extract basenames for cleaner context
                    file_names = [os.path.basename(p) for p in catalog_paths]
                    # Format as bullet points
                    catalog_list = [f"- {name}" for name in file_names[:50]] # Limit to 50
                    if len(file_names) > 50:
                        catalog_list.append(f"...and {len(file_names)-50} more.")
                    
                    catalog_str = "\n".join(catalog_list)
                    system_prompt += f"\n\nAVAILABLE KNOWLEDGE BASE (Files in Database):\n{catalog_str}\n"
                    print(f"[DEBUG] Injected catalog into system prompt. Catalog length: {len(catalog_str)}", flush=True)
                else:
                    print("[DEBUG] No files found in index to inject.", flush=True)
            except Exception as e:
                print(f"Catalog injection error: {e}", flush=True)
            
            # Append Vision Context (if any)
            if vision_context:
                 system_prompt += vision_context
                 
            print(f"[DEBUG] FINAL SYSTEM PROMPT:\n{system_prompt}\n[END PROMPT]", flush=True)

        # 3. Construct Message Chain
        # We need to rebuild the message list for the chat model
        # The 'history' variable is a list of dicts. We convert to LangChain messages.
        messages = [SystemMessage(content=system_prompt)] # History is handled via message construction below
        
        # Add past history (limit to last 10 turns to fit context)
        # session_messages = get_messages(session_id) 
        # (This is already passed as 'history' arg effectively, but we constructed text. 
        # For tools, we need Message objects. Let's use the raw history if possible,
        # but for now we'll rely on the text representation in system prompt or construct simple history)
        
        # Simpler approach: Just append the User's current query
        messages.append(HumanMessage(content=query))

        def generate_agent_stream():
            full_response = []  # Accumulate response for DB storage
            try:
                # --- TURN 1: Initial Generation ---
                ai_msg = llm_with_tools.invoke(messages)
                
                # Check for Tool Calls
                if ai_msg.tool_calls:
                    for tool_call in ai_msg.tool_calls:
                        tool_name = tool_call["name"].lower()
                        tool_args = tool_call["args"]
                        tool_id = tool_call["id"]
                        
                        # A. Security Check
                        requires_approval, reason = analyze_tool_call(tool_name, tool_args)
                        
                        if requires_approval:
                            # Yield Approval Request to Frontend
                            approval_data = {
                                "tool": tool_name,
                                "args": tool_args,
                                "id": tool_id,
                                "reason": reason,
                                "timestamp": time.time()
                            }
                            clean_pending_actions() # Clean before adding new
                            PENDING_ACTIONS[session_id] = approval_data
                            yield f"[APPROVAL_REQUIRED] {json.dumps(approval_data)}"
                            return

                        # B. Safe Execution
                        yield f"🤖 Use Tool: `{tool_name}`...\n"
                        
                        action_function = TOOL_REGISTRY.get(tool_name)
                        if action_function:
                            if tool_name == "ingest_document" or tool_name == "delete_document":
                                result_json = action_function(**tool_args)
                            else:
                                result_json = action_function()
                                
                            messages.append(ai_msg)
                            messages.append(ToolMessage(content=result_json, tool_call_id=tool_id))
                            
                            yield f"✅ Tool Result: {result_json}\n\n"
                        else:
                            yield f"❌ Error: Tool {tool_name} not found.\n"

                    # --- TURN 2: Final Response after Tool Execution ---
                    for chunk in llm.stream(messages):
                         content = chunk.content
                         if content:
                             full_response.append(content)
                             yield content
                else:
                    # No tools used - stream the response
                    response_content = ai_msg.content
                    if response_content:
                        full_response.append(response_content)
                        yield response_content
                    else:
                        # Fallback: try to get text representation
                        fallback = str(ai_msg) if ai_msg else "I couldn't generate a response. Please try again."
                        full_response.append(fallback)
                        yield fallback

            except Exception as e:
                traceback.print_exc()
                error_msg = f"\n\n[Error: {str(e)}]"
                full_response.append(error_msg)
                yield error_msg
            
            finally:
                # ALWAYS save assistant response at end of generator (runs on completion or error)
                final_response = "".join(full_response) if full_response else "[No response generated]"
                add_message(session_id, 'assistant', final_response[:2000])  # Truncate if too long

        # ========================================
        # SAVE USER MESSAGE IMMEDIATELY (BEFORE STREAMING)
        # ========================================
        # This ensures user message is saved even if stream is interrupted
        file_meta = []
        if files:
            file_meta = [{"name": f.get("name"), "type": f.get("type", "document"), "path": f"/uploaded_files/{f.get('name')}"} for f in files]
        
        add_message(session_id, 'user', query, metadata={"files": file_meta})

        # Return the streaming response
        return Response(generate_agent_stream(), mimetype='text/plain')

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ==========================================
# AGENTIC APPROVAL ENDPOINT
# ==========================================
# Global store for pending actions
PENDING_ACTIONS = {}

def clean_pending_actions(ttl=300): # 5 minutes TTL
    """Remove stale pending actions."""
    current_time = time.time()
    to_remove = []
    for sid, data in PENDING_ACTIONS.items():
        if current_time - data.get("timestamp", 0) > ttl:
            to_remove.append(sid)
    
    for sid in to_remove:
        del PENDING_ACTIONS[sid]

@app.route("/api/agent/allow", methods=["POST"])
def allow_tool():
    """Execute a pending tool call after user approval."""
    clean_pending_actions() # Clean stale actions    # Parse request
    data = request.json or {}
    session_id = data.get("session_id")
    query = data.get("message", "")
    temp_doc_content = data.get("temp_doc_content", None)
    images = data.get("images", []) # List of {name, data (base64)}
    use_deep_search = data.get("deep_search", False)
    
    # Validation
    if not query and not images:
        return jsonify({"error": "No message or images provided"}), 400
        
    pending = PENDING_ACTIONS.get(session_id)
    if not pending or pending["id"] != action_id:
        return jsonify({"error": "No matching pending action found."}), 404
    
    # Clear pending
    del PENDING_ACTIONS[session_id]
    
    if decision != "approve":
        return jsonify({"status": "denied", "message": "Action cancelled by user."})
    
    # Execute Tool
    tool_name = pending["tool"]
    tool_args = pending["args"]
    
    action_function = TOOL_REGISTRY.get(tool_name)
    if not action_function:
         return jsonify({"error": f"Tool {tool_name} not found"}), 500
         
    try:
        # Execute
        result_json = action_function(**tool_args) if tool_args else action_function()
        
        # In a real agent loop, we would feed this back to LLM.
        # For Phase 1, we just return the result to the UI.
        return jsonify({
            "status": "success", 
            "result": result_json,
            "tool": tool_name
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500





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



def is_cli_running():
    """Check if the CLI chat process is running."""
    try:
        if os.name == 'nt':
            # Windows: Check for python process with chat.py in command line
            cmd = 'wmic process where "name=\'python.exe\'" get commandline'
            output = subprocess.check_output(cmd, shell=True).decode()
            return "chat.py" in output
        else:
            # Unix/Linux
            cmd = "ps -ef | grep chat.py | grep -v grep"
            output = subprocess.check_output(cmd, shell=True).decode()
            return "chat.py" in output
    except:
        return False

def launch_cli():
    """Launch the CLI chat in a new window."""
    print("Launching CLI Chat...", flush=True)
    if os.name == 'nt':
        # Launch in a new command prompt window
        subprocess.Popen(f'start "Onyx CLI" cmd /k "{sys.executable}" chat.py', shell=True, cwd=os.getcwd())
    else:
        # Unix/Linux standard terminal emulators
        terminals = ["x-terminal-emulator", "gnome-terminal", "konsole", "xterm"]
        for term in terminals:
            if shutil.which(term):
                subprocess.Popen([term, "-e", f"{sys.executable} chat.py"])
                return
        # Fallback
        subprocess.Popen([sys.executable, "chat.py"])






# ============== MODEL MANAGEMENT API ==============

@app.route("/api/models", methods=["GET"])
def api_list_models():
    """Get list of available Ollama models."""
    config = load_config()
    ollama_host = config.get("ollama_host", "http://localhost:11434")
    models = list_models(ollama_host)
    return jsonify({"models": models, "count": len(models)})

@app.route("/api/models/pull", methods=["POST"])
def api_pull_model():
    """Pull a new model from Ollama."""
    data = request.json
    model_name = data.get("name")
    if not model_name:
        return jsonify({"error": "Model name required"}), 400
    
    return Response(pull_model_stream(model_name), mimetype='application/x-ndjson')

@app.route("/api/models/<path:model_name>", methods=["DELETE"])
def api_delete_model(model_name):
    """Delete a model."""
    success, msg = delete_model(model_name)
    if success:
        return jsonify({"status": "success", "message": msg})
    return jsonify({"error": msg}), 500

# ============== NEW API ENDPOINTS ==============
@app.route("/api/tasks/<task_id>", methods=["GET"])
def get_task_status(task_id):
    """Check status of a background task."""
    task = TASKS.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)


@app.route("/api/health", methods=["GET"])
def api_health():
    """Get system health status including Ollama and model availability."""
    try:
        status = get_system_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/system/ollama/control", methods=["POST"])
def api_control_ollama():
    """Control the Ollama service (Start/Restart/Stop)."""
    data = request.json
    action = data.get("action")
    
    if action not in ["start", "restart", "stop"]:
        return jsonify({"error": "Invalid action. Use start, restart, or stop"}), 400
        
    try:
        msg = f"Ollama {action} initiated"
        
        if action == "stop" or action == "restart":
            # Windows-specific kill
            if sys.platform == "win32":
                subprocess.run("taskkill /IM ollama.exe /F", shell=True, stderr=subprocess.DEVNULL)
                subprocess.run("taskkill /IM ollama_app.exe /F", shell=True, stderr=subprocess.DEVNULL)
            else:
                subprocess.run("pkill -9 ollama", shell=True, stderr=subprocess.DEVNULL)
            
            # Wait for cleanup with timeout
            time.sleep(2) 
            
        if action == "start" or action == "restart":
            # Start Ollama deeply detached
            if sys.platform == "win32":
                # Use CREATE_NEW_CONSOLE | DETACHED_PROCESS to run completely independent
                # This prevents it from being a child that dies with the server or blocks
                DETACHED_PROCESS = 0x00000008
                CREATE_NEW_PROCESS_GROUP = 0x00000200
                subprocess.Popen(
                    ["ollama", "serve"],
                    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                    shell=True, # shell=True needed to find 'ollama' in PATH usually, but Popen with list implies no shell? 
                    # Actually for shell=True, args should be string. For list, shell=False. 
                    # Let's use string with shell=True but DETACHED.
                )
                # Re-do: Popen(["ollama", "serve"]) with creationflags is safer if in PATH
                # If 'ollama' is a command, we might need shell=True to find it if it's a batch file/shim? 
                # Usually ollama.exe is a binary.
                # Let's try shell=True with "start" to be safe as before, but verify flags.
                # User reported "Won't work at all". 
                # Let's try direct execution.
                subprocess.Popen(
                    "ollama serve", 
                    shell=True, 
                    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            else:
                subprocess.Popen(
                    ["ollama", "serve"],
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            # Brief wait to let it spawn
            time.sleep(3)
            
        return jsonify({"status": "success", "message": msg})
        
    except Exception as e:
        logger.error(f"Error controlling Ollama: {e}")
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
    return jsonify({"error": "Session not found or rename failed"}), 404


# export_session REMOVED - using /api/sessions/<id>/export at line 168


@app.route("/api/index/stats", methods=["GET"])
def index_stats():
    """Get statistics about the vector index."""
    stats = get_index_stats()
    return jsonify(stats)


@app.route("/api/browser/sync", methods=["POST"])
def sync_browser():
    """Endpoint for Chrome Extension to send active tab data."""
    try:
        data = request.json or {}
        session_id = request.headers.get('X-Session-ID', 'default')
        logger.debug(f"Browser Sync Request. Session-ID: {session_id}")
        
        BROWSER_SESSIONS[session_id] = {
            "url": data.get("url", ""),
            "title": data.get("title", ""),
            "content": data.get("content", ""),
            "timestamp": time.time()
        }
        return jsonify({"status": "synced", "session_id": session_id})
    except Exception as e:
        print(f"Error in browser sync: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/browser/context", methods=["GET"])
def get_browser_context():
    """Get the currently synced browser context."""
    session_id = request.headers.get('X-Session-ID', 'default')
    return jsonify(BROWSER_SESSIONS.get(session_id, {}))


@app.route("/api/browser/clear", methods=["POST"])
def clear_browser_context():
    """Clear the browser context."""
    session_id = request.headers.get('X-Session-ID', 'default')
    if session_id in BROWSER_SESSIONS:
        del BROWSER_SESSIONS[session_id]
    return jsonify({"status": "cleared", "session_id": session_id})


@app.route("/api/stats", methods=["GET"])
def app_stats():
    """Get aggregated application statistics for the dashboard."""
    try:
        # Get index stats
        idx_stats = get_index_stats()
        
        # Get session stats
        sessions = get_all_sessions()
        total_sessions = len(sessions)
        
        # Calculate total messages efficiently with single query
        total_messages = get_total_message_count()
            
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
        # Get indexed files once at the beginning (cached already, but still avoid repeated calls)
        indexed_files_set = set(get_indexed_files())
        
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
                    "indexed": filename in indexed_files_set
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
    
    # Defaults
    defaults = {"current_session_id": None, "mode": "browser", "sessions": [], "models": [], "history": []}
    try:
        config = load_config()
        defaults["mode"] = config.get("mode", "browser")
        defaults["config"] = config
    except:
        defaults["config"] = {}

    return render_template("index.html", **defaults, message="Page not found", status="error")


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    traceback.print_exc()
    if request.path.startswith('/api/'):
        return jsonify({"error": "Internal server error"}), 500
        
    # Defaults
    defaults = {"current_session_id": None, "mode": "browser", "sessions": [], "models": [], "history": []}
    try:
        config = load_config()
        defaults["mode"] = config.get("mode", "browser")
        defaults["config"] = config
    except:
        defaults["config"] = {}
        
    return render_template("index.html", **defaults, message="Server error occurred", status="error")


# ------------------------------------------------------------------
# API: Pinned Sessions
# ------------------------------------------------------------------
@app.route("/api/sessions/<int:session_id>/pin", methods=["POST"])
def pin_session(session_id):
    """Toggle pin status."""
    data = request.json
    is_pinned = data.get("is_pinned", False)
    success = toggle_pin_session(session_id, is_pinned)
    return jsonify({"success": success})

@app.route("/api/pinned_sessions", methods=["GET"])
def get_pinned():
    """Get all pinned sessions."""
    sessions = get_pinned_sessions()
    return jsonify(sessions)

@app.route("/api/sessions/<int:session_id>/rename", methods=["PUT"])
def rename_session_endpoint(session_id):
    """Rename a session."""
    data = request.json
    new_name = data.get("name")
    if not new_name:
        return jsonify({"error": "New name is required"}), 400
        
    success = rename_session(session_id, new_name)
    return jsonify({"success": success})

# ------------------------------------------------------------------
# API: Prompt Library
# ------------------------------------------------------------------
@app.route("/api/prompts", methods=["GET", "POST"])
def manage_prompts():
    """Manage usage prompts."""
    if request.method == "POST":
        data = request.json
        title = data.get("title")
        content = data.get("content")
        tags = data.get("tags", "")
        if not title or not content:
            return jsonify({"error": "Missing title or content"}), 400
        
        prompt_id = create_prompt(title, content, tags)
        return jsonify({"success": True, "id": prompt_id})
    else:
        prompts = get_all_prompts()
        return jsonify(prompts)

@app.route("/api/prompts/<int:prompt_id>", methods=["DELETE"])
def delete_prompt_endpoint(prompt_id):
    """Delete a prompt."""
    success = delete_prompt(prompt_id)
    return jsonify({"success": success})

# ------------------------------------------------------------------
# API: Configuration & Settings
# ------------------------------------------------------------------
@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    """Get or update application settings."""
    if request.method == "POST":
        try:
            data = request.json or {}
            update_config(data)
            return jsonify({"status": "success", "message": "Settings updated"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        try:
            config = load_config()
            return jsonify(config)
        except Exception as e:
            return jsonify({"error": str(e)}), 500


def start_cli():
    """Launch the CLI in a new terminal window."""
    try:
        cli_script = os.path.join(BASE_DIR, "chat.py")
        CLI_LOCK = os.path.join(BASE_DIR, ".cli_opened")
        
        # 1. Attempt Atomic Lock Acquisition
        try:
            # 'x' mode creates file, failing if it exists (Atomic)
            with open(CLI_LOCK, 'x') as f:
                f.write(str(time.time()))
            # Lock acquired -> Launch
            logger.info("CLI lock acquired. Launching...")
            if sys.platform == "win32":
                subprocess.Popen(f'start "Onyx CLI" cmd /k "python {cli_script}"', shell=True)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-a", "Terminal", "python", cli_script])
            else: # Linux
                subprocess.Popen(["x-terminal-emulator", "-e", "python", cli_script])
            return
        except FileExistsError:
            logger.info("CLI lock exists. verifying...")

        # 2. Check if lock is RECENT (Race condition protection)
        try:
            with open(CLI_LOCK, 'r') as f:
                content = f.read().strip()
                if content:
                    timestamp = float(content)
                    if time.time() - timestamp < 5:
                        logger.info("CLI lock is recent (< 5s). Assuming startup in progress. skipping.")
                        return
        except Exception as e:
            logger.warning(f"Failed to read lock timestamp: {e}")

        # 3. Verify if process is actually running (Handle stale locks)
        is_running = False
        if sys.platform == "win32":
            try:
                # Check for window title using tasklist filter
                check_cmd = 'tasklist /FI "WINDOWTITLE eq Onyx CLI*" /FO CSV /NH'
                output = subprocess.run(check_cmd, capture_output=True, text=True, shell=True).stdout
                # Valid process output in CSV contains quotes and commas, e.g. "cmd.exe","1234",...
                if '","' in output or "WindowsTerminal" in output or "cmd.exe" in output:
                    is_running = True
            except:
                pass
        
        if is_running:
            logger.info("CLI process verified running. Focusing...")
            if sys.platform == "win32":
                subprocess.run("powershell -c \"(New-Object -ComObject WScript.Shell).AppActivate('Onyx CLI')\"", shell=True)
            return
        else:
            logger.info("CLI lock found but process not running (stale). Cleaning up and retrying...")
            try:
                os.remove(CLI_LOCK)
                start_cli() # Retry launch
            except Exception as e:
                logger.error(f"Error during stale lock cleanup: {e}")

    except Exception as e:
        logger.error(f"Failed to launch CLI: {e}")

@app.route("/set_mode", methods=["POST"])
def set_mode():
    """Set operation mode (CLI or Browser)."""
    try:
        data = request.json
        mode = data.get("mode")
        if mode not in ["cli", "browser"]:
            return jsonify({"error": "Invalid mode"}), 400
            
        # Update and save config
        update_config({"mode": mode})
        
        # Launch CLI if requested
        if mode == "cli":
            start_cli()
            
        return jsonify({"status": "success", "mode": mode})
    except Exception as e:
        return jsonify({"error": str(e)}), 500






@app.route("/")
def index():
    """Render the main chat interface."""
    config = load_config()
    
    # Get all sessions
    all_sessions = get_all_sessions()
    
    history = []
    
    # Get available models
    models = ["gemma3:270m", "llama2", "mistral", "neural-chat"]
    try:
        health = check_ollama_health(config.get("ollama_host"))
        if health["available"]:
             online_models = list_models(config.get("ollama_host"))
             if online_models:
                 models = online_models
    except:
        pass

    return render_template("index.html", 
                         sessions=all_sessions,
                         current_session_id=None,
                         history=history,
                         models=models,
                         mode=config.get("mode", "cli"))


# ------------------------------------------------------------------
# API: Global Search
# ------------------------------------------------------------------
@app.route("/api/search", methods=["GET"])
def global_search():
    """Search sessions, messages, and files."""
    query = request.args.get("q", "").lower()
    if len(query) < 2:
        return jsonify({"sessions": [], "messages": [], "files": []})
        
    # 1. Database Search (Sessions & Messages)
    db_results = search_chat_data(query)
    
    # 2. File System Search
    found_files = []
    if os.path.exists(UPLOAD_DIR):
        for filename in os.listdir(UPLOAD_DIR):
            if query in filename.lower():
                found_files.append(filename)
                
    return jsonify({
        "sessions": db_results["sessions"],
        "messages": db_results["messages"],
        "files": found_files
    })




if __name__ == "__main__":
    # Initialize the database
    from database import init_db
    init_db()
    
    config = load_config()
    logger.info(f"{'='*50}")
    logger.info("RAG Agent Web Server Starting...")
    logger.info(f"Model: {config.get('model', 'gemma3:270m')}")
    logger.info(f"Hybrid Search: {'Enabled' if config.get('use_hybrid_search') else 'Disabled'}")
    logger.info(f"{'='*50}")
    
    # Production run (default)
    app.run(host='127.0.0.1', port=8501, debug=True)
