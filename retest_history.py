
import requests
import sqlite3
import time
import sys
import os

DB_PATH = "chat_history.db"
BASE_URL = "http://127.0.0.1:8501"

def test_history():
    print(f"Testing History Persistence against {BASE_URL}")
    
    # 1. Check Health (Retry loop)
    for i in range(5):
        try:
            print(f"Attempt {i+1} to connect...")
            resp = requests.get(f"{BASE_URL}/api/health", timeout=10)
            if resp.status_code == 200:
                print("✅ Server is reachable")
                break
        except Exception as e:
            print(f"⚠️ Connection failed: {e}")
            time.sleep(2)
    else:
        print("❌ Server unreachable after 5 attempts")
        return

    # 2. Send Message
    msg_content = f"HISTORY_VERIFICATION_{int(time.time())}"
    print(f"Sending message: {msg_content}")
    try:
        payload = {"message": msg_content}
        resp = requests.post(f"{BASE_URL}/chat", json=payload, timeout=30) # 30s timeout
        
        print(f"Response: {resp.status_code} {resp.text[:100]}...")
            
    except Exception as e:
        print(f"❌ Chat Request failed: {e}")

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
            
    except Exception as e:
        print(f"❌ Database check failed: {e}")

if __name__ == "__main__":
    test_history()
