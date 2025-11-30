import subprocess
import time
import webbrowser
import sys
import shutil
import chat

REQUIRED_MODELS = ["gemma3:270m", "qwen2.5:0.5b", "nomic-embed-text"]

def check_dependencies():
    """Checks if Ollama is installed and models are pulled."""
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
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
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
            
    except subprocess.CalledProcessError:
        print("\n❌ Error: Failed to communicate with Ollama. Is the server running?")
        sys.exit(1)

def start():
    check_dependencies()
    print("Initializing the Agent...")
    
    # 1. Start Flask UI in background
    ui = subprocess.Popen(
        [sys.executable, "app.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # 2. Open Browser
    time.sleep(2)
    webbrowser.open("http://localhost:8501")
    
    # 3. Start Terminal Chat
    try:
        chat.main()
    except KeyboardInterrupt:
        pass
    finally:
        print("\n🛑 Shutting down system...")
        ui.terminate()
        sys.exit()

if __name__ == "__main__":
    start()
