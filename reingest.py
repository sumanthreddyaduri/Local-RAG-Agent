
import requests
import os

API_URL = "http://localhost:8501/api"
UPLOAD_DIR = "./uploaded_files"

def reingest_all():
    # 1. Get list of files in upload dir
    if not os.path.exists(UPLOAD_DIR):
        print("Upload directory not found.")
        return

    files = [f for f in os.listdir(UPLOAD_DIR) if os.path.isfile(os.path.join(UPLOAD_DIR, f))]
    print(f"Found {len(files)} files to ingest: {files}")

    if not files:
        return

    # 2. Call ingest API
    response = requests.post(f"{API_URL}/files/ingest", json={"files": files})
    
    if response.status_code == 200:
        print("Ingestion successful!")
        print(response.json())
    else:
        print(f"Ingestion failed: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    reingest_all()
