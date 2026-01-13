import subprocess
import time
import webbrowser
import sys
import shutil
import os

REQUIRED_MODELS = ["gemma2:2b", "gemma3:270m", "qwen2.5:0.5b", "nomic-embed-text", "moondream"]
LOCK_DIR = os.path.dirname(os.path.abspath(__file__))
BROWSER_LOCK = os.path.join(LOCK_DIR, ".browser_opened")
CLI_LOCK = os.path.join(LOCK_DIR, ".cli_opened")

SETUP_MARKER = os.path.join(LOCK_DIR, ".setup_done")

def check_dependencies():
    """Checks if Ollama is installed and models are pulled. Skipped if already verified."""
    
    force_check = "--force-check" in sys.argv
    
    if os.path.exists(SETUP_MARKER) and not force_check:
        print("Skipping dependency check (already satisfied).")
        return

    print("Checking system dependencies...")
    
    # 1. Check Ollama
    if not shutil.which("ollama"):
        print("\nError: Ollama is not installed or not in your PATH.")
        print("Please download it from https://ollama.com")
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
            print(f"\nMissing models: {', '.join(missing_models)}")
            print("   Downloading them now (this might take a while)...")
            for model in missing_models:
                print(f"   Pulling {model}...")
                subprocess.run(["ollama", "pull", model], check=True)
            print("All models ready!")
        
        # Mark setup as done
        with open(SETUP_MARKER, 'w') as f:
            f.write(str(time.time()))
            
    except subprocess.TimeoutExpired:
        print("\nWarning: Ollama check timed out. Assuming models are present to avoid startup delay.")
    except subprocess.CalledProcessError:
        print("\nError: Failed to communicate with Ollama. Is the server running?")
        sys.exit(1)


def is_server_running():
    """Check if the Flask server is already running on port 8501."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', 8501))
        return result == 0
    except Exception:
        return False
    finally:
        sock.close()

def cleanup_locks():
    """Remove lock files on clean shutdown."""
    for lock in [BROWSER_LOCK, CLI_LOCK]:
        if os.path.exists(lock):
            try:
                os.remove(lock)
            except OSError:
                pass

def start():
    check_dependencies()
    
    server_was_running = is_server_running()
    
    if server_was_running:
        print("Server restart detected. Continuing...")
    else:
        print("Initializing Hybrid Architecture...")
        # Fresh start - clean stale locks
        cleanup_locks()
    
    # Determine launch requirements BEFORE starting server to prevent race conditions
    should_launch_cli = not os.path.exists(CLI_LOCK)
    should_launch_browser = not os.path.exists(BROWSER_LOCK)

    # Reserve locks immediately to prevent race conditions with app.py
    if should_launch_cli:
        with open(CLI_LOCK, 'w') as f:
            f.write(str(time.time()))
            
    if should_launch_browser:
        with open(BROWSER_LOCK, 'w') as f:
            f.write(str(time.time()))

    # 1. Start Flask UI in background (if not already running)
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
    
    # 2. Open Browser ONLY if reserved
    if should_launch_browser:
        port = 8501 
        print(f"Opening browser at http://127.0.0.1:{port}")
        webbrowser.open(f'http://127.0.0.1:{port}')
    else:
        print("Browser already open. Skipping browser launch.")
    
    # 3. Start Terminal Chat ONLY if reserved
    if should_launch_cli:
        print("\nLaunching CLI Chat in a new window...")
        cli_script = "chat.py"
        if sys.platform == 'win32':
             # Use absolute path for robustness
             cli_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), cli_script)
             subprocess.Popen(f'start "Onyx CLI" cmd /k "python {cli_path}"', shell=True)
        else:
             subprocess.Popen(["x-terminal-emulator", "-e", f"{sys.executable} {cli_script}"])
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
