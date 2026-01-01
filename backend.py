"""
Enhanced RAG Backend with Hybrid Search, Configurable Settings, and Better Error Handling.
"""

import os
import pickle
import re
import traceback
import logging
from typing import List, Tuple, Optional, Any
from collections import Counter
import math

from langchain_community.document_loaders import (
    PyPDFLoader, TextLoader, Docx2txtLoader, 
    UnstructuredExcelLoader, UnstructuredPowerPointLoader, CSVLoader
)
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from config_manager import load_config, get_config_value

# BM25 index storage path
# Helper to determine BM25 path based on DB path
def get_bm25_path(db_path: str) -> str:
    """Get the path for the BM25 index, associated with the vector DB."""
    # If db_path is a directory (FAISS default), put bm25 inside or sibling
    # Sibling is safer if db_path assumes strictly FAISS files
    # But inside keeps it self-contained. Let's do sibling with suffix.
    # Actually, user suggested os.path.join(db_path, "bm25_index.pkl").
    # If FAISS load_local expects only its own files, this might pollute it?
    # FAISS usually ignores extra files. Putting it inside is cleaner organization.
    return os.path.join(db_path, "bm25_index.pkl")

# Global cache variables for performance optimization
_CACHED_DB = None
_CACHED_BM25 = None
_CACHED_RETRIEVER = None
_CACHED_LLM = None
_CACHED_MODEL_NAME = None
_CACHED_CONFIG = None # To detect config changes (db_path, embed_model)

# ... (BM25Index class remains similar, just update save/load to take path passed to it) ...

# ... (HybridRetriever remains same) ...

# ... (get_loader, load_document_content remain same) ...

def ingest_files(file_paths: List[str]) -> Tuple[bool, str]:
    """
    Reads files, chunks them, and saves to Vector DB and BM25 index.
    Uses configurable chunk size and overlap.
    """
    config = load_config()
    db_path = config.get('db_path', 'faiss_index')
    embed_model = config.get('embed_model', 'nomic-embed-text')
    chunk_size = config.get('chunk_size', 1000)
    chunk_overlap = config.get('chunk_overlap', 200)
    
    bm25_path = get_bm25_path(db_path)
    
    all_docs = []
    failed_files = []
    
    for path in file_paths:
        try:
            loader = get_loader(path)
            docs = loader.load()
            # Add source metadata and prepend source to content for better retrieval
            for doc in docs:
                doc.metadata['source'] = os.path.basename(path)
                doc.metadata['full_path'] = path
                # Prepend source to content so keyword search for filename matches the document
                doc.page_content = f"Source: {os.path.basename(path)}\n\n{doc.page_content}"
            all_docs.extend(docs)
        except Exception as e:
            failed_files.append(f"{os.path.basename(path)}: {str(e)}")

    if not all_docs:
        if failed_files:
            return False, f"Failed to load files:\n" + "\n".join(failed_files)
        return False, "No valid content found in the uploaded files."

    # Split text for RAG using configured chunk size
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, 
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    splits = splitter.split_documents(all_docs)

    try:
        # Save to FAISS
        embeddings = OllamaEmbeddings(model=embed_model)
        
        if os.path.exists(db_path):
            db = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)
            db.add_documents(splits)
        else:
            db = FAISS.from_documents(splits, embeddings)
        
        db.save_local(db_path)
        
        # Build/update BM25 index
        bm25_index = BM25Index.load(bm25_path)
        if bm25_index:
            # Add new documents to existing index
            all_bm25_docs = bm25_index.documents + splits
            bm25_index.fit(all_bm25_docs)
        else:
            bm25_index = BM25Index()
            bm25_index.fit(splits)
        
        bm25_index.save(bm25_path)
        
    except Exception as e:
        return False, f"Error during indexing: {str(e)}"
    
    if failed_files:
        success_msg = f"Indexed {len(all_docs)} files, but {len(failed_files)} failed.\nFailures:\n" + "\n".join(failed_files)
        # Return False if partial failure is considered effectively "not full success"? 
        # Or True but with warning? API usually prefers True if at least some worked.
        # But user feedback says "Misleading Success".
        # Let's return True but make message very clear.
        # Or return False? If I return False, UI might show Error toast.
        # Ideally: Partial Success.
        pass
    else:
        success_msg = f"Success! Indexed {len(all_docs)} files."
    
    # Clear cache to force reload with new documents
    clear_rag_cache()
    
    return True, success_msg


def get_vector_store() -> Optional[FAISS]:
    """
    Get the FAISS vector store, using cache if available.
    Invalidates cache if configuration (path/model) changes.
    """
    global _CACHED_DB, _CACHED_CONFIG
    
    config = load_config()
    db_path = config.get('db_path', 'faiss_index')
    embed_model = config.get('embed_model', 'nomic-embed-text')
    ollama_host = config.get('ollama_host', 'http://localhost:11434')
    
    current_config = {
        "db_path": db_path, 
        "embed_model": embed_model,
        "ollama_host": ollama_host
    }
    
    # Check cache validity
    if _CACHED_DB is not None and _CACHED_CONFIG == current_config:
        return _CACHED_DB
        
    if not os.path.exists(db_path):
        return None
        
    try:
        if _CACHED_DB is not None:
             print("→ Configuration changed, reloading vector store...")
        else:
             print("→ Loading FAISS index from disk (cache miss)...")
             
        embeddings = OllamaEmbeddings(model=embed_model, base_url=ollama_host)
        _CACHED_DB = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)
        _CACHED_CONFIG = current_config # Update config cache
        return _CACHED_DB
    except Exception as e:
        print(f"Error loading vector store: {e}")
        return None


def get_rag_chain(model_name: str = None) -> Tuple[Optional[Any], ChatOllama]:
    # ... (Update logic using get_vector_store and get_bm25_path) ...
    global _CACHED_RETRIEVER, _CACHED_LLM, _CACHED_MODEL_NAME, _CACHED_BM25
    
    config = load_config()
    db_path = config.get('db_path', 'faiss_index')
    bm25_path = get_bm25_path(db_path)
    
    if model_name is None:
        model_name = config.get('model', 'gemma3:270m')
    
    use_hybrid = config.get('use_hybrid_search', True)
    hybrid_alpha = config.get('hybrid_alpha', 0.5)
    retrieval_k = config.get('retrieval_k', 3)
    ollama_host = config.get('ollama_host', 'http://localhost:11434')
    
    # Check if we need a new LLM (model changed)
    if _CACHED_LLM is None or _CACHED_MODEL_NAME != model_name:
        _CACHED_LLM = ChatOllama(model=model_name, base_url=ollama_host)
        _CACHED_MODEL_NAME = model_name
    
    llm = _CACHED_LLM
    
    # Get vector store (handling cache/config changes)
    db = get_vector_store()
    if db is None:
        return None, llm
        
    # Check if retriever is still valid (config might have changed in get_vector_store which cleared DB but not Retriever?)
    # If get_vector_store reloaded, _CACHED_DB changed object.
    # We should track if retriever is stale.
    # Simple way: if get_vector_store returned a different object than what retriever is built on... difficult to check.
    # Better: If _CACHED_CONFIG changed in get_vector_store, we need to rebuild retriever.
    # But get_vector_store doesn't return that info.
    # We can check global _CACHED_RETRIEVER again. 
    # Actually, if we just clear _CACHED_RETRIEVER in get_vector_store if it reloads?
    # No, get_vector_store is getter.
    
    # Let's verify config here too or trust get_vector_store.
    # If we cache Retriever, we must ensure it matches current DB.
    # If get_vector_store reloads, it updates _CACHED_DB.
    # If _CACHED_RETRIEVER exists, does it point to old DB? Yes.
    # So we need to invalidate _CACHED_RETRIEVER when DB reloads.
    pass

def clear_rag_cache():
    """Clear the RAG cache. Call after ingest_files or clear_index to force reload."""
    global _CACHED_DB, _CACHED_BM25, _CACHED_RETRIEVER, _CACHED_CONFIG
    _CACHED_DB = None
    _CACHED_BM25 = None
    _CACHED_RETRIEVER = None
    _CACHED_CONFIG = None

def clear_index() -> Tuple[bool, str]:
    config = load_config()
    db_path = config.get('db_path', 'faiss_index')
    bm25_path = get_bm25_path(db_path)
    
    try:
        import shutil
        if os.path.exists(db_path):
            shutil.rmtree(db_path)
        if os.path.exists(bm25_path):
            os.remove(bm25_path)
        # Clear cache to reflect cleared index
        clear_rag_cache()
        return True, "Index cleared successfully."
    except Exception as e:
        return False, f"Error clearing index: {str(e)}"


def remove_document(filename: str) -> Tuple[bool, str]:
    """
    Removes a specific document from FAISS and BM25 indices.
    """
    config = load_config()
    db_path = config.get('db_path', 'faiss_index')
    bm25_path = get_bm25_path(db_path)
    
    try:
        # 1. Update FAISS
        db = get_vector_store()
        if db:
            # Find IDs to delete
            ids_to_delete = []
            for doc_id, doc in db.docstore._dict.items():
                if doc.metadata.get('source') == filename:
                    ids_to_delete.append(doc_id)
            
            if ids_to_delete:
                db.delete(ids_to_delete)
                db.save_local(db_path)
        
        # 2. Update BM25
        if os.path.exists(bm25_path):
            bm25_index = BM25Index.load(bm25_path)
            if bm25_index:
                # Filter out documents with matching source
                # Note: This checks doc.metadata. Using page_content prefix might be needed if metadata lost, 
                # but our ingest preserves metadata.
                initial_count = len(bm25_index.documents)
                bm25_index.documents = [d for d in bm25_index.documents if d.metadata.get('source') != filename]
                
                if len(bm25_index.documents) < initial_count:
                    # Re-fit to update stats
                    bm25_index.fit(bm25_index.documents)
                    bm25_index.save(bm25_path)

        # Clear cache
        clear_rag_cache()
        return True, f"Successfully removed {filename} from index."
        
    except Exception as e:
        return False, f"Error removing document: {str(e)}"



class BM25Index:
    """
    Simple BM25 implementation for keyword-based retrieval.
    Used as part of hybrid search.
    """
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: List[Document] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_length: float = 0
        self.doc_freqs: Counter = Counter()
        self.idf: dict = {}
        self.doc_term_freqs: List[Counter] = []
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization: lowercase and split on non-alphanumeric."""
        return re.findall(r'\w+', text.lower())
    
    def fit(self, documents: List[Document]):
        """Build the BM25 index from documents."""
        self.documents = documents
        self.doc_term_freqs = []
        self.doc_lengths = []
        
        # Calculate term frequencies for each document
        for doc in documents:
            tokens = self._tokenize(doc.page_content)
            self.doc_lengths.append(len(tokens))
            term_freq = Counter(tokens)
            self.doc_term_freqs.append(term_freq)
            
            # Update document frequencies (how many docs contain each term)
            for term in set(tokens):
                self.doc_freqs[term] += 1
        
        self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths) if self.doc_lengths else 0
        
        # Calculate IDF for each term
        n_docs = len(documents)
        for term, df in self.doc_freqs.items():
            self.idf[term] = math.log((n_docs - df + 0.5) / (df + 0.5) + 1)
    
    def search(self, query: str, k: int = 5) -> List[Tuple[Document, float]]:
        """Search for documents matching the query."""
        if not self.documents:
            return []
        
        query_tokens = self._tokenize(query)
        scores = []
        
        for i, doc in enumerate(self.documents):
            score = 0
            doc_len = self.doc_lengths[i]
            term_freqs = self.doc_term_freqs[i]
            
            for token in query_tokens:
                if token in term_freqs:
                    tf = term_freqs[token]
                    idf = self.idf.get(token, 0)
                    
                    # BM25 formula
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avg_doc_length))
                    score += idf * (numerator / denominator)
            
            scores.append((doc, score))
        
        # Sort by score and return top k
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]
    
    def save(self, path: str):
        """Save the BM25 index to disk."""
        with open(path, 'wb') as f:
            pickle.dump({
                'documents': self.documents,
                'doc_lengths': self.doc_lengths,
                'avg_doc_length': self.avg_doc_length,
                'doc_freqs': self.doc_freqs,
                'idf': self.idf,
                'doc_term_freqs': self.doc_term_freqs,
                'k1': self.k1,
                'b': self.b
            }, f)
    
    @classmethod
    def load(cls, path: str) -> Optional['BM25Index']:
        """Load the BM25 index from disk."""
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)
            
            index = cls(k1=data.get('k1', 1.5), b=data.get('b', 0.75))
            index.documents = data['documents']
            index.doc_lengths = data['doc_lengths']
            index.avg_doc_length = data['avg_doc_length']
            index.doc_freqs = data['doc_freqs']
            index.idf = data['idf']
            index.doc_term_freqs = data.get('doc_term_freqs', [])
            return index
        except Exception as e:
            print(f"Error loading BM25 index: {e}")
            return None


class HybridRetriever:
    """
    Combines vector search (FAISS) with keyword search (BM25) for better retrieval.
    """
    
    def __init__(self, vector_store: FAISS, bm25_index: BM25Index, alpha: float = 0.5):
        """
        Args:
            vector_store: FAISS vector store for semantic search
            bm25_index: BM25 index for keyword search
            alpha: Weight for vector search (1-alpha for BM25). Default 0.5 = equal weight
        """
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        self.alpha = alpha
    
    def get_relevant_documents(self, query: str, k: int = 5) -> List[Document]:
        """Retrieve documents using hybrid search."""
        # Get vector search results
        vector_results = self.vector_store.similarity_search_with_score(query, k=k*2)
        
        # Get BM25 results
        bm25_results = self.bm25_index.search(query, k=k*2)
        
        # Normalize and combine scores
        doc_scores = {}
        
        # Process vector results (lower distance = better)
        if vector_results:
            max_dist = max(r[1] for r in vector_results) or 1
            for doc, dist in vector_results:
                # Convert distance to similarity score (0-1)
                score = 1 - (dist / max_dist) if max_dist > 0 else 1
                doc_id = doc.page_content[:100]  # Use content prefix as ID
                doc_scores[doc_id] = {
                    'doc': doc,
                    'vector_score': score * self.alpha,
                    'bm25_score': 0
                }
        
        # Process BM25 results
        if bm25_results:
            max_bm25 = max(r[1] for r in bm25_results) or 1
            for doc, score in bm25_results:
                if score > 0:
                    normalized = score / max_bm25
                    doc_id = doc.page_content[:100]
                    if doc_id in doc_scores:
                        doc_scores[doc_id]['bm25_score'] = normalized * (1 - self.alpha)
                    else:
                        doc_scores[doc_id] = {
                            'doc': doc,
                            'vector_score': 0,
                            'bm25_score': normalized * (1 - self.alpha)
                        }
        
        # Calculate final scores and sort
        results = []
        for doc_id, data in doc_scores.items():
            total_score = data['vector_score'] + data['bm25_score']
            results.append((data['doc'], total_score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return [doc for doc, score in results[:k]]
    
    def invoke(self, query: str) -> List[Document]:
        """LangChain-compatible invoke method."""
        config = load_config()
        k = config.get('retrieval_k', 3)
        return self.get_relevant_documents(query, k=k)


def get_loader(file_path: str):
    """Factory to pick the right loader for the file type."""
    ext = os.path.splitext(file_path)[1].lower()
    loaders = {
        ".pdf": lambda: PyPDFLoader(file_path),
        ".txt": lambda: TextLoader(file_path, encoding="utf-8"),
        ".md": lambda: TextLoader(file_path, encoding="utf-8"),
        ".docx": lambda: Docx2txtLoader(file_path),
        ".csv": lambda: CSVLoader(file_path),
        ".xlsx": lambda: UnstructuredExcelLoader(file_path, mode="elements"),
        ".xls": lambda: UnstructuredExcelLoader(file_path, mode="elements"),
        ".pptx": lambda: UnstructuredPowerPointLoader(file_path),
        ".ppt": lambda: UnstructuredPowerPointLoader(file_path),
        ".xaml": lambda: TextLoader(file_path, encoding="utf-8"),
    }
    
    if ext not in loaders:
        raise ValueError(f"Unsupported file type: {ext}. Supported: {', '.join(loaders.keys())}")
    
    return loaders[ext]()


def load_document_content(file_path: str) -> str:
    """
    Load document content as plain text using LangChain loaders.
    Same loaders used for RAG ingestion - ensures consistent parsing.
    
    Args:
        file_path: Path to the document file
        
    Returns:
        Extracted text content from the document
    """
    try:
        loader = get_loader(file_path)
        docs = loader.load()
        # Combine all pages/chunks into single text
        content = "\n\n".join([doc.page_content for doc in docs if doc.page_content.strip()])
        return content if content else "(Document appears to be empty)"
    except ValueError as e:
        # Unsupported file type
        return f"(Unsupported file type: {str(e)})"
    except Exception as e:
        return f"(Error reading document: {str(e)[:200]})"


def ingest_files(file_paths: List[str]) -> Tuple[bool, str]:
    """
    Reads files, chunks them, and saves to Vector DB and BM25 index.
    Uses configurable chunk size and overlap.
    """
    config = load_config()
    db_path = config.get('db_path', 'faiss_index')
    embed_model = config.get('embed_model', 'nomic-embed-text')
    chunk_size = config.get('chunk_size', 1000)
    chunk_overlap = config.get('chunk_overlap', 200)
    
    bm25_path = get_bm25_path(db_path)
    
    all_docs = []
    failed_files = []
    
    for path in file_paths:
        try:
            loader = get_loader(path)
            docs = loader.load()
            # Add source metadata and prepend source to content for better retrieval
            for doc in docs:
                doc.metadata['source'] = os.path.basename(path)
                doc.metadata['full_path'] = path
                # Prepend source to content so keyword search for filename matches the document
                doc.page_content = f"Source: {os.path.basename(path)}\n\n{doc.page_content}"
            all_docs.extend(docs)
        except Exception as e:
            failed_files.append(f"{os.path.basename(path)}: {str(e)}")

    if not all_docs:
        if failed_files:
            return False, f"Failed to load files:\n" + "\n".join(failed_files)
        return False, "No valid content found in the uploaded files."

    # Split text for RAG using configured chunk size
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, 
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    splits = splitter.split_documents(all_docs)

    try:
        # Save to FAISS
        embeddings = OllamaEmbeddings(model=embed_model)
        
        if os.path.exists(db_path):
            db = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)
            db.add_documents(splits)
        else:
            db = FAISS.from_documents(splits, embeddings)
        
        db.save_local(db_path)
        
        # Build/update BM25 index
        bm25_index = BM25Index.load(bm25_path)
        if bm25_index:
            # Add new documents to existing index
            all_bm25_docs = bm25_index.documents + splits
            bm25_index.fit(all_bm25_docs)
        else:
            bm25_index = BM25Index()
            bm25_index.fit(splits)
        
        bm25_index.save(bm25_path)
        
    except Exception as e:
        return False, f"Error during indexing: {str(e)}"
    
    success_msg = f"Success! Indexed {len(all_docs)} files."
    if failed_files:
        success_msg += f"\nWarning: Some files failed:\n" + "\n".join(failed_files)
    
    # Clear cache to force reload with new documents
    clear_rag_cache()
    
    return True, success_msg


def get_vector_store() -> Optional[FAISS]:
    """
    Get the FAISS vector store, using cache if available.
    Invalidates cache if configuration (path/model) changes.
    """
    global _CACHED_DB, _CACHED_CONFIG, _CACHED_RETRIEVER
    
    config = load_config()
    db_path = config.get('db_path', 'faiss_index')
    embed_model = config.get('embed_model', 'nomic-embed-text')
    ollama_host = config.get('ollama_host', 'http://localhost:11434')
    
    current_config = {
        "db_path": db_path, 
        "embed_model": embed_model,
        "ollama_host": ollama_host
    }
    
    # Check cache validity
    if _CACHED_DB is not None and _CACHED_CONFIG == current_config:
        return _CACHED_DB
        
    if not os.path.exists(db_path):
        return None
        
    try:
        if _CACHED_DB is not None:
             print("> Configuration changed, reloading vector store...")
             # Important: Invalidate derived objects too
             _CACHED_RETRIEVER = None
        else:
             print("> Loading FAISS index from disk (cache miss)...")
             
        embeddings = OllamaEmbeddings(model=embed_model, base_url=ollama_host)
        _CACHED_DB = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)
        _CACHED_CONFIG = current_config # Update config cache
        return _CACHED_DB
    except Exception as e:
        print(f"Error loading vector store: {e}")
        return None


def get_rag_chain(model_name: str = None) -> Tuple[Optional[Any], ChatOllama]:
    """
    Returns the Retrieval Chain with the selected model.
    Uses global caching to prevent disk I/O on every chat call.
    Supports hybrid search if enabled in config.
    """
    global _CACHED_RETRIEVER, _CACHED_LLM, _CACHED_MODEL_NAME, _CACHED_BM25
    
    config = load_config()
    db_path = config.get('db_path', 'faiss_index')
    # Dynamic BM25 path
    bm25_path = get_bm25_path(db_path)
    
    if model_name is None:
        model_name = config.get('model', 'gemma3:270m')
            
    use_hybrid = config.get('use_hybrid_search', True)
    hybrid_alpha = config.get('hybrid_alpha', 0.5)
    retrieval_k = config.get('retrieval_k', 3)
    ollama_host = config.get('ollama_host', 'http://localhost:11434')
    
    # Check if we need a new LLM (model changed)
    if _CACHED_LLM is None or _CACHED_MODEL_NAME != model_name:
        _CACHED_LLM = ChatOllama(model=model_name, base_url=ollama_host)
        _CACHED_MODEL_NAME = model_name
    
    llm = _CACHED_LLM
    
    # Get vector store (handles config changes)
    db = get_vector_store()
    if db is None:
        return None, llm
    
    # Return cached retriever if available (and valid - ensured by get_vector_store clearing it)
    if _CACHED_RETRIEVER is not None:
        print(f"✓ Using cached retriever (cache hit)")
        return _CACHED_RETRIEVER, llm
    
    try:
        if use_hybrid:
            # Load BM25 index from dynamic path
            if _CACHED_BM25 is None:
                _CACHED_BM25 = BM25Index.load(bm25_path)
            
            if _CACHED_BM25:
                _CACHED_RETRIEVER = HybridRetriever(db, _CACHED_BM25, alpha=hybrid_alpha)
                return _CACHED_RETRIEVER, llm
        
        # Fall back to vector-only search
        _CACHED_RETRIEVER = db.as_retriever(search_kwargs={"k": retrieval_k})
        return _CACHED_RETRIEVER, llm
        
    except Exception as e:
        print(f"Error initializing retriever: {e}")
        return None, llm


def clear_rag_cache():
    """Clear the RAG cache. Call after ingest_files or clear_index to force reload."""
    global _CACHED_DB, _CACHED_BM25, _CACHED_RETRIEVER, _CACHED_CONFIG
    _CACHED_DB = None
    _CACHED_BM25 = None
    _CACHED_RETRIEVER = None
    _CACHED_CONFIG = None


def clear_index() -> Tuple[bool, str]:
    """Clear all indexed documents."""
    config = load_config()
    db_path = config.get('db_path', 'faiss_index')
    bm25_path = get_bm25_path(db_path)
    
    try:
        import shutil
        if os.path.exists(db_path):
            shutil.rmtree(db_path)
        if os.path.exists(bm25_path):
            os.remove(bm25_path)
        # Clear cache to reflect cleared index
        clear_rag_cache()
        return True, "Index cleared successfully."
    except Exception as e:
        return False, f"Error clearing index: {str(e)}"


def get_indexed_files() -> List[str]:
    """Get list of files that have been indexed."""
    db = get_vector_store()
    
    if not db:
        return []
    
    try:
        # Get unique sources from docstore
        sources = set()
        for doc_id in db.docstore._dict:
            doc = db.docstore._dict[doc_id]
            if hasattr(doc, 'metadata') and 'source' in doc.metadata:
                sources.add(doc.metadata['source'])
        
        return sorted(list(sources))
    except Exception as e:
        print(f"Error getting indexed files: {e}")
        return []


def get_index_stats() -> dict:
    """Get statistics about the current index."""
    stats = {
        "total_chunks": 0,
        "total_files": 0,
        "files": [],
        "bm25_available": False
    }
    
    db = get_vector_store()
    
    if not db:
        return stats
    
    try:
        stats["total_chunks"] = len(db.docstore._dict)
        stats["files"] = get_indexed_files()
        stats["total_files"] = len(stats["files"])
        stats["bm25_available"] = os.path.exists(BM25_INDEX_PATH)
        
    except Exception as e:
        print(f"Error getting index stats: {e}")
    
    return stats


def get_knowledge_graph(max_docs: int = 50, top_terms_per_doc: int = 5) -> dict:
    """
    Generates a knowledge graph structure (nodes, links) from the BM25 index.
    Nodes: Documents and High-IDF Terms.
    Links: Document <-> Term.
    """
    try:
        config = load_config()
        db_path = config.get('db_path', 'faiss_index')
        bm25_path = get_bm25_path(db_path)
        
        graph = {"nodes": [], "links": []}
        
        if not os.path.exists(bm25_path):
            return graph

        bm25 = BM25Index.load(bm25_path)
        if not bm25 or not bm25.documents:
            return graph
            
        docs_to_process = bm25.documents[:max_docs]
        term_nodes = set()
        
        for i in range(min(len(bm25.documents), max_docs)):
            doc = bm25.documents[i]
            doc_name = doc.metadata.get('source', f"Doc {i}")
            doc_name = os.path.basename(doc_name)
            doc_id = f"doc_{i}"
            
            graph["nodes"].append({
                "id": doc_id,
                "label": doc_name,
                "type": "document",
                "group": 1,
                "radius": 12 
            })
            
            # Check safely for doc_term_freqs
            if not hasattr(bm25, 'doc_term_freqs') or i >= len(bm25.doc_term_freqs):
                continue

            term_freqs = bm25.doc_term_freqs[i]
            
            scored_terms = []
            for term, count in term_freqs.items():
                if term in bm25.idf:
                    score = count * bm25.idf[term]
                    if bm25.idf[term] > 0.5: 
                        scored_terms.append((term, score))
            
            scored_terms.sort(key=lambda x: x[1], reverse=True)
            top_terms = scored_terms[:top_terms_per_doc]
            
            for term, score in top_terms:
                term_id = f"term_{term}"
                if term not in term_nodes:
                    graph["nodes"].append({
                        "id": term_id,
                        "label": term,
                        "type": "term",
                        "group": 2,
                        "radius": 6
                    })
                    term_nodes.add(term)
                
                graph["links"].append({
                    "source": doc_id,
                    "target": term_id,
                    "value": score
                })
        return graph

    except Exception as e:
        print(f"Error generating graph: {e}")
        traceback.print_exc()
        return {"nodes": [], "links": [], "error": str(e)}
