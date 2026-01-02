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
        result = ingest_files(files)
        print(f"Processed: {result['processed_count']}, Failed: {result['failed_count']}")
        for res in result["results"]:
            status_icon = "✅" if res["status"] == "success" else "❌"
            print(f"{status_icon} {res['file']}: {res['message']}")
    else:
        print("No files to ingest.")

if __name__ == "__main__":
    reingest()
