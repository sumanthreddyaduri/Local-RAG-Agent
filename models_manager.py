import subprocess
import json
import threading
import time
import requests

def list_models(host="http://localhost:11434"):
    """
    List available models from Ollama.
    Returns a list of dicts: {'name': 'gemma3:270m', 'size': '1.7GB', 'modified': '...'}
    """
    try:
        # Try API first (faster/cleaner)
        response = requests.get(f"{host}/api/tags", timeout=2)
        if response.status_code == 200:
            data = response.json()
            models = []
            for m in data.get("models", []):
                # Convert size to human readable
                size_bytes = m.get("size", 0)
                size_str = f"{size_bytes / (1024**3):.1f} GB" if size_bytes > 1024**3 else f"{size_bytes / (1024**2):.1f} MB"
                
                models.append({
                    "name": m["name"],
                    "size": size_str,
                    "modified": m.get("modified_at", "")
                })
            return models
    except:
        # Fallback to CLI
        pass

    try:
        # Fallback: Parse 'ollama list' output
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        if result.returncode != 0:
            return []
            
        lines = result.stdout.strip().split('\n')
        models = []
        # Skip header (NAME ID SIZE MODIFIED)
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 3:
                name = parts[0]
                # Simple parsing, might need refinement for spaces in dates
                # But typically: name  id  size  modified...
                models.append({
                    "name": name,
                    "size": "Unknown", # CLI parsing is brittle for size
                    "modified": ""
                })
        return models
    except Exception as e:
        print(f"Error listing models: {e}")
        return []

def delete_model(model_name):
    """Delete a model via Ollama CLI."""
    try:
        subprocess.run(["ollama", "rm", model_name], check=True, capture_output=True)
        return True, "Model deleted successfully"
    except subprocess.CalledProcessError as e:
        return False, f"Failed to delete: {e.stderr.decode()}"
    except Exception as e:
        return False, str(e)

def pull_model_stream(model_name):
    """
    Generator that pulls a model and yields progress updates.
    Yields JSON strings: {"status": "pulling", "progress": 45, "total": 100}
    """
    try:
        process = subprocess.Popen(
            ["ollama", "pull", model_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        for line in process.stdout:
            # Parse Ollama's CLI output for progress
            # Example: "pulling manifest" or "downloading layer ... 10%"
            yield json.dumps({"status": "progress", "message": line.strip()}) + "\n"
            
        process.wait()
        if process.returncode == 0:
            yield json.dumps({"status": "success", "message": f"Successfully pulled {model_name}"}) + "\n"
        else:
            yield json.dumps({"status": "error", "message": "Pull failed with non-zero exit code"}) + "\n"
            
    except Exception as e:
        yield json.dumps({"status": "error", "message": str(e)}) + "\n"
