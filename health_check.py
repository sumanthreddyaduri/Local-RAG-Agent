"""
Health check utilities for external service dependencies.
"""

import requests
from typing import Dict, Any, Optional
import time


def check_ollama_health(host: str = "http://localhost:11434", timeout: int = 5) -> Dict[str, Any]:
    """
    Check if Ollama is running and responsive.
    
    Returns:
        Dict with status, available models, and any error messages.
    """
    result = {
        "status": "unknown",
        "available": False,
        "models": [],
        "error": None,
        "response_time_ms": None
    }
    
    try:
        start_time = time.time()
        
        # Check if Ollama is responding
        response = requests.get(f"{host}/api/tags", timeout=timeout)
        
        result["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
        
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            result["status"] = "healthy"
            result["available"] = True
            result["models"] = [m.get("name", m.get("model", "unknown")) for m in models]
        else:
            result["status"] = "unhealthy"
            result["error"] = f"Unexpected status code: {response.status_code}"
            
    except requests.exceptions.ConnectionError:
        result["status"] = "offline"
        result["error"] = "Cannot connect to Ollama. Is it running?"
    except requests.exceptions.Timeout:
        result["status"] = "timeout"
        result["error"] = f"Ollama did not respond within {timeout} seconds"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    
    return result


def check_model_available(model_name: str, host: str = "http://localhost:11434") -> Dict[str, Any]:
    """
    Check if a specific model is available in Ollama.
    
    Returns:
        Dict with availability status and model info.
    """
    result = {
        "model": model_name,
        "available": False,
        "error": None
    }
    
    health = check_ollama_health(host)
    
    if not health["available"]:
        result["error"] = health["error"]
        return result
    
    # Check if model is in the list
    available_models = [m.lower() for m in health["models"]]
    model_lower = model_name.lower()
    
    # Check for exact match or prefix match (for versioned models)
    for available in available_models:
        if available == model_lower or available.startswith(model_lower.split(':')[0]):
            result["available"] = True
            break
    
    if not result["available"]:
        result["error"] = f"Model '{model_name}' not found. Available: {', '.join(health['models'])}"
    
    return result


def pull_model(model_name: str, host: str = "http://localhost:11434") -> Dict[str, Any]:
    """
    Trigger Ollama to pull/download a model.
    
    Returns:
        Dict with status of the pull operation.
    """
    result = {
        "model": model_name,
        "status": "unknown",
        "error": None
    }
    
    try:
        response = requests.post(
            f"{host}/api/pull",
            json={"name": model_name},
            timeout=300  # Long timeout for model download
        )
        
        if response.status_code == 200:
            result["status"] = "success"
        else:
            result["status"] = "failed"
            result["error"] = response.text
            
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    
    return result


def get_system_status() -> Dict[str, Any]:
    """
    Get comprehensive system status including all dependencies.
    """
    from config_manager import load_config
    
    config = load_config()
    ollama_host = config.get("ollama_host", "http://localhost:11434")
    current_model = config.get("model", "gemma3:270m")
    embed_model = config.get("embed_model", "nomic-embed-text")
    
    ollama_health = check_ollama_health(ollama_host)
    
    status = {
        "ollama": ollama_health,
        "current_model": check_model_available(current_model, ollama_host),
        "embed_model": check_model_available(embed_model, ollama_host),
        "config_valid": True,
        "db_exists": False,
        "indexed_files": 0
    }
    
    # Check if vector DB exists
    import os
    db_path = config.get("db_path", "faiss_index")
    if os.path.exists(db_path) and os.path.exists(os.path.join(db_path, "index.faiss")):
        status["db_exists"] = True
    
    return status
