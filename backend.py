import os
from langchain_community.document_loaders import (
    PyPDFLoader, TextLoader, Docx2txtLoader, 
    UnstructuredExcelLoader, UnstructuredPowerPointLoader, CSVLoader
)
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Configuration
DB_PATH = "faiss_index"
EMBED_MODEL = "nomic-embed-text"

def get_loader(file_path):
    """Factory to pick the right loader for the file type."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf": return PyPDFLoader(file_path)
    elif ext in [".txt", ".md"]: return TextLoader(file_path, encoding="utf-8")
    elif ext == ".docx": return Docx2txtLoader(file_path)
    elif ext == ".csv": return CSVLoader(file_path)
    elif ext in [".xlsx", ".xls"]: return UnstructuredExcelLoader(file_path, mode="elements")
    elif ext in [".pptx", ".ppt"]: return UnstructuredPowerPointLoader(file_path)
    else: raise ValueError(f"Unsupported file type: {ext}")

def ingest_files(file_paths):
    """Reads files, chunks them, and saves to Vector DB."""
    all_docs = []
    for path in file_paths:
        try:
            loader = get_loader(path)
            all_docs.extend(loader.load())
        except Exception as e:
            return False, f"Error loading {path}: {str(e)}"

    if not all_docs: return False, "No valid content found."

    # Split text for RAG
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = splitter.split_documents(all_docs)

    # Save to FAISS
    embeddings = OllamaEmbeddings(model=EMBED_MODEL)
    if os.path.exists(DB_PATH):
        db = FAISS.load_local(DB_PATH, embeddings, allow_dangerous_deserialization=True)
        db.add_documents(splits)
    else:
        db = FAISS.from_documents(splits, embeddings)
    
    db.save_local(DB_PATH)
    return True, f"Success! Indexed {len(all_docs)} files ({len(splits)} chunks)."

def get_rag_chain(model_name):
    """Returns the Retrieval Chain with the selected model."""
    embeddings = OllamaEmbeddings(model=EMBED_MODEL)
    if not os.path.exists(DB_PATH):
        return None, ChatOllama(model=model_name)
        
    db = FAISS.load_local(DB_PATH, embeddings, allow_dangerous_deserialization=True)
    return db.as_retriever(search_kwargs={"k": 3}), ChatOllama(model=model_name)
