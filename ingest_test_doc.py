from backend import ingest_files
import os

# Ensure absolute path
file_path = os.path.abspath("test_doc.txt")
print(f"Ingesting {file_path}...")
success, msg = ingest_files([file_path])
print(msg)
