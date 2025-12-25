import requests
import json
import time

BASE_URL = "http://localhost:8501"

def check_health():
    try:
        resp = requests.get(f"{BASE_URL}/api/health")
        print(f"Health Check: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))
        return resp.status_code == 200
    except Exception as e:
        print(f"Health Check Failed: {e}")
        return False

def test_chat(query):
    print(f"\nTesting Query: '{query}'")
    try:
        # Use stream=False to get text, or handle stream
        # The backend returns streaming text.
        resp = requests.post(
            f"{BASE_URL}/chat", 
            json={"message": query, "session_id": 999},
            stream=True
        )
        
        print("Response Status:", resp.status_code)
        
        full_text = ""
        for line in resp.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                full_text += decoded
                # print(decoded, end="", flush=True)
        
        print("\nFull Response:", full_text)
        return full_text
    except Exception as e:
        print(f"Chat Test Failed: {e}")
        return None

if __name__ == "__main__":
    if check_health():
        # 1. Test File Awareness (Catalog)
        # test_chat("What files do you have in your database?")
        
        # 2. Test Retrieval (RAG)
        test_chat("What is the content of debug_doc.txt?")
