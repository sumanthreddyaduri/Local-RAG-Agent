"""
Configuration management for the RAG Agent.
Provides default settings and validation.
"""

import json
import os
from typing import Any, Dict

CONFIG_FILE = "config.json"

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
    """Load configuration from file, using defaults for missing values."""
    config = DEFAULT_CONFIG.copy()
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                saved_config = json.load(f)
                # Merge saved config with defaults (saved values take precedence)
                config.update(saved_config)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load config file: {e}")
    
    return config


def save_config(config: Dict[str, Any]) -> bool:
    """Save configuration to file."""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
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
    
    # Validate chunk_size
    if not isinstance(config.get('chunk_size'), int) or config['chunk_size'] < 100:
        errors.append("chunk_size must be an integer >= 100")
    
    # Validate chunk_overlap
    if not isinstance(config.get('chunk_overlap'), int) or config['chunk_overlap'] < 0:
        errors.append("chunk_overlap must be a non-negative integer")
    
    if config.get('chunk_overlap', 0) >= config.get('chunk_size', 1000):
        errors.append("chunk_overlap must be less than chunk_size")
    
    # Validate retrieval_k
    if not isinstance(config.get('retrieval_k'), int) or config['retrieval_k'] < 1:
        errors.append("retrieval_k must be a positive integer")
    
    # Validate hybrid_alpha
    alpha = config.get('hybrid_alpha', 0.5)
    if not isinstance(alpha, (int, float)) or alpha < 0 or alpha > 1:
        errors.append("hybrid_alpha must be between 0 and 1")
    
    # Validate max_history_context
    if not isinstance(config.get('max_history_context'), int) or config['max_history_context'] < 0:
        errors.append("max_history_context must be a non-negative integer")
    
    return len(errors) == 0, errors


# Initialize config file with defaults if it doesn't exist
if not os.path.exists(CONFIG_FILE):
    save_config(DEFAULT_CONFIG)
