
import os
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from config_manager import load_config

def inspect_index():
    config = load_config()
    db_path = config.get('db_path', 'faiss_index')
    embed_model = config.get('embed_model', 'nomic-embed-text')
    
    print(f"Inspecting index at: {db_path}")
    print(f"Using embedding model: {embed_model}")
    
    if not os.path.exists(db_path):
        print("Index directory does not exist.")
        return
    
    try:
        embeddings = OllamaEmbeddings(model=embed_model)
        db = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)
        
        print(f"Total chunks in index: {len(db.docstore._dict)}")
        
        sources = set()
        for doc_id, doc in db.docstore._dict.items():
            if hasattr(doc, 'metadata'):
                source = doc.metadata.get('source', 'UNKNOWN_SOURCE')
                sources.add(source)
                # print(f"Doc ID: {doc_id}, Source: {source}") # Too verbose
        
        print("\n=== Unique Files in Index ===")
        for s in sorted(list(sources)):
            print(f"- {s}")
            
        print(f"\nTotal unique files: {len(sources)}")
        
    except Exception as e:
        print(f"Error loading index: {e}")

if __name__ == "__main__":
    inspect_index()
