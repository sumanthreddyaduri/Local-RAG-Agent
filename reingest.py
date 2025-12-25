import os
import glob
from backend import ingest_files, clear_index

UPLOAD_DIR = "./uploaded_files"

def reingest():
    print("Clearing old index...")
    clear_index()
    
    files = glob.glob(os.path.join(UPLOAD_DIR, "*"))
    print(f"Found {len(files)} files to re-ingest: {files}")
    
    if files:
        success, msg = ingest_files(files)
        print(msg)
    else:
        print("No files to ingest.")

if __name__ == "__main__":
    reingest()
