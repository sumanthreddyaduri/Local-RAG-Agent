import os
import json
import logging
from security import SAFE_ROOT, is_safe_path
from backend import ingest_files, clear_index

logger = logging.getLogger(__name__)

# ====================
# TOOL FUNCTIONS
# ====================

def list_files():
    """Lists all files in the secure workspace."""
    try:
        files = os.listdir(SAFE_ROOT)
        return json.dumps({"status": "success", "files": files})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def ingest_document(filename):
    """
    Ingests a file that is ALREADY in the uploaded_files directory.
    Note: The Agent doesn't 'upload' from user PC, it operates on files 
    that have been placed in the secure directory.
    """
    if not is_safe_path(filename):
        return json.dumps({"status": "error", "message": "Access Denied: Path outside sandbox."})
    
    filepath = os.path.join(SAFE_ROOT, filename)
    if not os.path.exists(filepath):
        return json.dumps({"status": "error", "message": f"File '{filename}' not found."})

    try:
        # Ingest just this file
        # We might need to refactor backend.ingest_files to handle single list
        # Currently ingest_files takes 'file_paths' list
        result = ingest_files([filepath])
        if result:
            return json.dumps({"status": "success", "message": f"Successfully ingested {filename}"})
        else:
            return json.dumps({"status": "error", "message": "Ingestion backend returned false"})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def delete_document(filename):
    """
    Deletes a file and updates the RAG index.
    """
    if not is_safe_path(filename):
        return json.dumps({"status": "error", "message": "Access Denied: Path outside sandbox."})
    
    filepath = os.path.join(SAFE_ROOT, filename)
    if not os.path.exists(filepath):
        return json.dumps({"status": "error", "message": "File not found."})
    
    try:
        os.remove(filepath)
        
        # Remove from Index
        from backend import remove_document
        success, msg = remove_document(filename)
        
        if success:
            return json.dumps({"status": "success", "message": f"Deleted {filename} from disk and index."})
        else:
            return json.dumps({"status": "warning", "message": f"Deleted from disk, but index update failed: {msg}"})
            
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

# ====================
# REGISTRY & DEFINITIONS
# ====================

TOOL_REGISTRY = {
    "list_files": list_files,
    "ingest_document": ingest_document,
    "delete_document": delete_document
}

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List all files currently in the RAG memory/workspace.",
            "parameters": {
                "type": "object",
                "properties": {},
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ingest_document",
            "description": "Process and memorize a specific file. Use this when the user asks to 'read', 'learn', or 'ingest' a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the file to ingest (e.g. 'report.pdf')"
                    }
                },
                "required": ["filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_document",
            "description": "Permanently delete a file from the workspace. REQUIRES USER APPROVAL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the file to delete"
                    }
                },
                "required": ["filename"]
            }
        }
    }
]
