"""
Configuration management for the RAG Agent.
Provides default settings and validation with caching.
"""

import json
import os
from typing import Any, Dict

CONFIG_FILE = "config.json"

# Cache for configuration to reduce file I/O
_config_cache = None
_config_mtime = None

DEFAULT_CONFIG = {
    # Model Settings
    "model": "gemma2:2b",
    "available_models": ["gemma2:2b", "gemma3:270m", "qwen2.5:0.5b"],  # Chat models only (not embed/vision)
    
    # Mode Settings
    "mode": "cli",  # 'cli' or 'browser'
    
    # RAG Settings
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "retrieval_k": 3,  # Number of documents to retrieve
    "use_hybrid_search": True,  # Enable BM25 + Vector hybrid search
    "hybrid_alpha": 0.5,  # Weight for vector search (1-alpha for BM25)
    "use_reranking": False,  # Enable reranking (requires additional model)
    
    # Embedding Settings
    "embed_model": "nomic-embed-text",
    
    # Chat Settings
    "max_history_context": 10,  # Number of previous messages to include in context
    "enable_tts": False,  # Text-to-speech for responses
    "stream_responses": True,
    
    # System Settings
    "ollama_host": "http://localhost:11434",
    "upload_dir": "./uploaded_files",
    "db_path": "faiss_index",
    
    # UI Settings
    "theme": "dark",
    "show_sources": True,  # Show source documents in responses
}


def load_config() -> Dict[str, Any]:
    """Load configuration from file with caching, using defaults for missing values."""
    global _config_cache, _config_mtime
    
    config = DEFAULT_CONFIG.copy()
    
    if os.path.exists(CONFIG_FILE):
        try:
            # Check if file has been modified since last cache
            current_mtime = os.path.getmtime(CONFIG_FILE)
            
            if _config_cache is not None and _config_mtime == current_mtime:
                # Return cached config
                return _config_cache.copy()
            
            # Load from file
            with open(CONFIG_FILE, "r") as f:
                saved_config = json.load(f)
                # Merge saved config with defaults (saved values take precedence)
                config.update(saved_config)
            
            # Update cache
            _config_cache = config.copy()
            _config_mtime = current_mtime
            
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load config file: {e}")
    
    return config


def save_config(config: Dict[str, Any]) -> bool:
    """Save configuration to file and invalidate cache."""
    global _config_cache, _config_mtime
    
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        
        # Invalidate cache to force reload
        _config_cache = None
        _config_mtime = None
        
        return True
    except IOError as e:
        print(f"Error saving config: {e}")
        return False


def update_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update specific configuration values and save."""
    config = load_config()
    config.update(updates)
    save_config(config)
    return config


def get_config_value(key: str, default: Any = None) -> Any:
    """Get a specific configuration value."""
    config = load_config()
    return config.get(key, default)


def reset_config() -> Dict[str, Any]:
    """Reset configuration to defaults."""
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG.copy()


def validate_config(config: Dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate configuration values."""
    errors = []
    
    # --- Type Coercion & Validation ---
    
    # helper to safely convert
    def safe_int(val, default):
        try: return int(val)
        except (ValueError, TypeError): return default

    def safe_float(val, default):
        try: return float(val)
        except (ValueError, TypeError): return default

    # 1. Coerce types if possible (modify config in place for cleanliness)
    if 'chunk_size' in config:
        config['chunk_size'] = safe_int(config['chunk_size'], DEFAULT_CONFIG['chunk_size'])
    if 'chunk_overlap' in config:
        config['chunk_overlap'] = safe_int(config['chunk_overlap'], DEFAULT_CONFIG['chunk_overlap'])
    if 'retrieval_k' in config:
        config['retrieval_k'] = safe_int(config['retrieval_k'], DEFAULT_CONFIG['retrieval_k'])
    if 'hybrid_alpha' in config:
        config['hybrid_alpha'] = safe_float(config['hybrid_alpha'], DEFAULT_CONFIG['hybrid_alpha'])
    if 'max_history_context' in config:
        config['max_history_context'] = safe_int(config['max_history_context'], DEFAULT_CONFIG['max_history_context'])
    
    # 2. logical/Boundary Checks
    
    # Validate chunk_size
    if config['chunk_size'] < 100:
        errors.append("chunk_size must be >= 100")
    
    # Validate chunk_overlap
    if config['chunk_overlap'] < 0:
        errors.append("chunk_overlap must be non-negative")
    
    if config['chunk_overlap'] >= config['chunk_size']:
        errors.append("chunk_overlap must be less than chunk_size")
    
    # Validate retrieval_k
    if config['retrieval_k'] < 1:
        errors.append("retrieval_k must be a positive integer")
    
    # Validate hybrid_alpha
    if not (0 <= config['hybrid_alpha'] <= 1):
        errors.append("hybrid_alpha must be between 0 and 1")
    
    # Validate max_history_context
    if config['max_history_context'] < 0:
        errors.append("max_history_context must be non-negative")

    # Validate Mode
    valid_modes = ["cli", "browser"]
    if config.get("mode") not in valid_modes:
        errors.append(f"mode must be one of {valid_modes}")

    # Validate Ollama Host (Basic URL check)
    host = config.get("ollama_host", "")
    if not host.startswith("http"):
        errors.append("ollama_host must start with http:// or https://")

    return len(errors) == 0, errors


# Initialize config file with defaults if it doesn't exist
if not os.path.exists(CONFIG_FILE):
    save_config(DEFAULT_CONFIG)
