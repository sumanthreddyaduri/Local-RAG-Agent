
import requests
import sys

BASE_URL = "http://127.0.0.1:8501"

def test_new_chat():
    print(f"Testing 'New Chat' API against {BASE_URL}")

    # 1. Create New Session
    try:
        print("POST /api/sessions ...")
        # Must send json even if empty to trigger Content-Type: application/json
        resp = requests.post(f"{BASE_URL}/api/sessions", json={}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            session_id = data.get('session_id')
            name = data.get('name')
            print(f"✅ Created Session: ID={session_id}, Name='{name}'")
        else:
            print(f"❌ Failed to create session: {resp.status_code} {resp.text}")
            return
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return

    # 2. List Sessions
    try:
        print("GET /api/sessions ...")
        resp = requests.get(f"{BASE_URL}/api/sessions", timeout=10)
        if resp.status_code == 200:
            sessions = resp.json()
            print(f"✅ Retrieved {len(sessions)} sessions.")
            
            # Verify our new session is there
            found = False
            for s in sessions:
                if s['id'] == session_id:
                    found = True
                    print(f"✅ Verified Session {session_id} exists in list.")
                    break
            
            if not found:
                print(f"❌ Session {session_id} NOT found in list!")
        else:
            print(f"❌ Failed to list sessions: {resp.status_code}")

    except Exception as e:
        print(f"❌ List request failed: {e}")

if __name__ == "__main__":
    test_new_chat()
