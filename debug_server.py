from app import app
from database import init_db
from config_manager import load_config
import sys

if __name__ == "__main__":
    # Initialize the database
    init_db()
    
    config = load_config()
    print(f"\n{'='*50}")
    print("Running in DEBUG Mode (Auto-Reload Enabled)")
    print(f"Model: {config.get('model', 'gemma3:270m')}")
    print(f"{'='*50}\n")
        
    # Run in debug mode
    app.run(host='127.0.0.1', port=8501, debug=True)
