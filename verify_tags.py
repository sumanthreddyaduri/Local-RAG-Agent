import requests
import json
import time

BASE_URL = "http://localhost:8501"

def run_test():
    # 1. List files
    print("Listing files...")
    try:
        resp = requests.get(f"{BASE_URL}/api/files")
        files = resp.json().get("files", [])
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    if not files:
        print("No files found. Please upload a file first.")
        # Try to upload a dummy file
        with open("dummy_tag_test.txt", "w") as f:
            f.write("This is a test file for tagging.")
        
        files_to_upload = {'files': open('dummy_tag_test.txt', 'rb')}
        requests.post(f"{BASE_URL}/upload", files=files_to_upload)
        time.sleep(1)
        resp = requests.get(f"{BASE_URL}/api/files")
        files = resp.json().get("files", [])
        
    if not files:
        print(" Still no files.")
        return

    target_file = files[0]['name']
    print(f"Testing with file: {target_file}")

    # 2. Set Tags
    print(f"Setting tags for {target_file}...")
    tags = ["test_tag", "finance"]
    resp = requests.post(f"{BASE_URL}/api/files/{target_file}/tags", json={"tags": tags})
    print(f"Set tags response: {resp.status_code} - {resp.text}")

    # 3. Verify Tags
    print("Verifying tags...")
    resp = requests.get(f"{BASE_URL}/api/files")
    files = resp.json().get("files", [])
    
    found = False
    for f in files:
        if f['name'] == target_file:
            print(f"File found. Tags: {f.get('tags')}")
            if "test_tag" in f.get('tags', []):
                print("SUCCESS: Tag 'test_tag' found.")
                found = True
            else:
                print("FAILURE: Tag not found.")
            break
            
    if not found:
        print("FAILURE: File not found in validation step.")

if __name__ == "__main__":
    run_test()
