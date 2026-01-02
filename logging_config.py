
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

def setup_logging(log_dir="logs", log_file="app.log", level=logging.INFO):
    """
    Setup structured logging with console and file handlers.
    """
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_path = os.path.join(log_dir, log_file)

    # improved format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 1. File Handler (Rotating)
    file_handler = RotatingFileHandler(
        log_path, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8' # 10MB
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # 2. Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    # Root Logger Configuration
    logging.basicConfig(
        level=level,
        handlers=[file_handler, console_handler]
    )
    
    # Silence noisy libraries
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return logging.getLogger("RAG_Agent")
