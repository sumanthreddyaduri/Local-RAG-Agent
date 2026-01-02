import subprocess
import time
import webbrowser
import sys
import shutil
import os
import chat

REQUIRED_MODELS = ["gemma2:2b", "gemma3:270m", "qwen2.5:0.5b", "nomic-embed-text", "moondream"]
LOCK_DIR = os.path.dirname(os.path.abspath(__file__))
BROWSER_LOCK = os.path.join(LOCK_DIR, ".browser_opened")
CLI_LOCK = os.path.join(LOCK_DIR, ".cli_opened")

SETUP_MARKER = os.path.join(LOCK_DIR, ".setup_done")

def check_dependencies():
    """Checks if Ollama is installed and models are pulled. Skipped if already verified."""
    
    force_check = "--force-check" in sys.argv
    
    if os.path.exists(SETUP_MARKER) and not force_check:
        print("⚡ Skipping dependency check (already satisfied).")
        return

    print("🔍 Checking system dependencies...")
    
    # 1. Check Ollama
    if not shutil.which("ollama"):
        print("\n❌ Error: Ollama is not installed or not in your PATH.")
        print("👉 Please download it from https://ollama.com")
        print("   If installed, ensure it is added to your system environment variables.")
        input("\nPress Enter to exit...")
        sys.exit(1)
        
    # 2. Check Models
    try:
        # Add timeout to prevent hanging
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True, timeout=10)
        installed_models = result.stdout
        
        missing_models = []
        for model in REQUIRED_MODELS:
            if model not in installed_models:
                missing_models.append(model)
        
        if missing_models:
            print(f"\n⚠️  Missing models: {', '.join(missing_models)}")
            print("   Downloading them now (this might take a while)...")
            for model in missing_models:
                print(f"   ⬇️  Pulling {model}...")
                subprocess.run(["ollama", "pull", model], check=True)
            print("✅ All models ready!")
        
        # Mark setup as done
        with open(SETUP_MARKER, 'w') as f:
            f.write(str(time.time()))
            
    except subprocess.TimeoutExpired:
        print("\n⚠️ Warning: Ollama check timed out. Assuming models are present to avoid startup delay.")
    except subprocess.CalledProcessError:
        print("\n❌ Error: Failed to communicate with Ollama. Is the server running?")
        sys.exit(1)


def is_server_running():
    """Check if the Flask server is already running on port 8501."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', 8501))
        return result == 0
    except:
        return False
    finally:
        sock.close()

def cleanup_locks():
    """Remove lock files on clean shutdown."""
    for lock in [BROWSER_LOCK, CLI_LOCK]:
        if os.path.exists(lock):
            try:
                os.remove(lock)
            except:
                pass

def start():
    check_dependencies()
    
    server_was_running = is_server_running()
    
    if server_was_running:
        print("Server restart detected. Continuing...")
    else:
        print("Initializing Hybrid Architecture...")
    
    # 1. Start Flask UI in background (if not already running)
    ui = None
    ui = None
    if not server_was_running:
        if "--debug" in sys.argv:
            print("🔧 Debug Mode Enabled")
            app_args = [sys.executable, "debug_server.py"]
        else:
            app_args = [sys.executable, "app.py"]
            
        ui = subprocess.Popen(
            app_args,
            # stdout=subprocess.DEVNULL, # Allow logs to show
            # stderr=subprocess.DEVNULL
        )
        time.sleep(5)
    
    # 2. Open Browser ONLY if not already opened
    browser_already_open = os.path.exists(BROWSER_LOCK)
    if not browser_already_open:
        port = 8501 # Define port for clarity
        print(f"Opening browser at http://127.0.0.1:{port}")
        webbrowser.open(f'http://127.0.0.1:{port}')
        # Create lock file to prevent future duplicates
        with open(BROWSER_LOCK, 'w') as f:
            f.write(str(time.time()))
    else:
        print("Browser already open. Skipping browser launch (refresh manually if needed).")
    
    # 3. Start Terminal Chat in New Window ONLY if not already opened
    cli_already_open = os.path.exists(CLI_LOCK)
    if not cli_already_open:
        print("\nLaunching CLI Chat in a new window...")
        if sys.platform == 'win32':
            subprocess.Popen(["start", "cmd", "/k", sys.executable, "chat.py"], shell=True)
        else:
            subprocess.Popen(["x-terminal-emulator", "-e", f"{sys.executable} chat.py"])
        # Create lock file
        with open(CLI_LOCK, 'w') as f:
            f.write(str(time.time()))
    else:
        print("CLI already open. Skipping CLI launch.")

    # 4. Lock Main Terminal
    print("\n" + "="*60)
    print("MAIN TERMINAL LOCKED")
    print("="*60)
    print("Continue in the Chat window.")
    print("You can switch the chat mode to CLI or Browser for advanced chat.")
    print("Press Ctrl+C to shutdown the entire system.")
    print("="*60)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down system...")
        cleanup_locks()
        if ui:
            ui.terminate()
        sys.exit()

if __name__ == "__main__":
    start()
