
import requests
import sqlite3
import time
import sys
import os

DB_PATH = "chat_history.db"
BASE_URL = "http://127.0.0.1:8501"

def test_history():
    print(f"Testing History Persistence against {BASE_URL}")
    
    # 1. Check Health
    try:
        resp = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if resp.status_code != 200:
            print(f"❌ Server not healthy: {resp.status_code}")
            return
        print("✅ Server is reachable")
    except Exception as e:
        print(f"❌ Failed to reach server: {e}")
        return

    # 2. Send Message
    msg_content = f"HISTORY_VERIFICATION_{int(time.time())}"
    print(f"Sending message: {msg_content}")
    try:
        # Note: /chat endpoint expects specific format
        payload = {"message": msg_content}
        resp = requests.post(f"{BASE_URL}/chat", json=payload, timeout=10)
        # 503 is acceptable if Ollama is offline, as long as it hit the server logic
        # But wait, app.py checks ollama health first. 
        # If ollama offline, it refuses to chat? 
        # Let's check app.py code snippet... 
        # "if not health['available']: return ... 503"
        # If 503, message might NOT be saved if check happens before logging?
        # Let's see. logic: get_current_session -> check health -> ... -> history_text ... -> llm.
        # It seems it doesn't save USER message if ollama down? 
        # Wait, usually history is saved BEFORE reasoning? 
        # Checking database.py usage in app.py would be good but I don't have it open.
        # Assuming typical flow: user msg -> save -> llm -> save response.
        
        if resp.status_code == 200:
            print("✅ Message sent successfully")
        elif resp.status_code == 503:
            print("⚠️ Ollama offline (503), checking if message was saved anyway...")
        else:
            print(f"❌ Failed to send message: {resp.status_code} {resp.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

    # 3. Check Database
    print("Checking database for persistence...")
    if not os.path.exists(DB_PATH):
        print("❌ Database file not found!")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM chat_messages WHERE content = ?", (msg_content,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            print(f"✅ FOUND message in database! ID: {row[0]}")
            print("History persistence is WORKING.")
        else:
            print("❌ Message NOT found in database.")
            print("Possible reasons: Ollama offline blocked saving, or DB error.")
            
    except Exception as e:
        print(f"❌ Database check failed: {e}")

if __name__ == "__main__":
    test_history()
