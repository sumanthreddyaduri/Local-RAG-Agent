import subprocess
import time
import webbrowser
import sys
import chat

def start():
    print("🚀 Initializing Hybrid Architecture...")
    
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
