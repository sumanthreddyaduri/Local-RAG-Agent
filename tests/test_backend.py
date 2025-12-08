"""
Comprehensive tests for the RAG Agent backend.
"""

import unittest
import os
import sys
import tempfile
import shutil

# Add parent dir to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import get_loader, BM25Index, ingest_files, get_index_stats, clear_index
from config_manager import load_config, save_config, update_config, validate_config, DEFAULT_CONFIG
from database import (
    init_db, create_session, get_session, get_all_sessions,
    add_message, get_messages, delete_session, rename_session,
    format_history_for_prompt, clear_session_messages
)


class TestLoaders(unittest.TestCase):
    """Test document loaders."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_loader_txt(self):
        """Test loading .txt files."""
        path = os.path.join(self.temp_dir, "test.txt")
        with open(path, "w") as f:
            f.write("Test content")
        loader = get_loader(path)
        self.assertIsNotNone(loader)
    
    def test_get_loader_md(self):
        """Test loading .md files."""
        path = os.path.join(self.temp_dir, "test.md")
        with open(path, "w") as f:
            f.write("# Test Markdown")
        loader = get_loader(path)
        self.assertIsNotNone(loader)
    
    def test_get_loader_pdf(self):
        """Test loading .pdf files."""
        path = os.path.join(self.temp_dir, "test.pdf")
        with open(path, "wb") as f:
            f.write(b"%PDF-1.4 test")
        loader = get_loader(path)
        self.assertIsNotNone(loader)
    
    def test_get_loader_invalid(self):
        """Test that invalid file types raise ValueError."""
        with self.assertRaises(ValueError) as context:
            get_loader("test.xyz")
        self.assertIn("Unsupported file type", str(context.exception))


class TestBM25Index(unittest.TestCase):
    """Test BM25 keyword search index."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.index_path = os.path.join(self.temp_dir, "test_bm25.pkl")
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_tokenize(self):
        """Test tokenization."""
        index = BM25Index()
        tokens = index._tokenize("Hello, World! This is a TEST.")
        self.assertEqual(tokens, ['hello', 'world', 'this', 'is', 'a', 'test'])
    
    def test_fit_and_search(self):
        """Test fitting and searching the index."""
        from langchain.schema import Document
        
        docs = [
            Document(page_content="Python is a programming language"),
            Document(page_content="JavaScript is used for web development"),
            Document(page_content="Python and JavaScript are both popular"),
        ]
        
        index = BM25Index()
        index.fit(docs)
        
        # Search for Python
        results = index.search("Python programming", k=2)
        self.assertEqual(len(results), 2)
        self.assertIn("Python", results[0][0].page_content)
    
    def test_save_and_load(self):
        """Test saving and loading the index."""
        from langchain.schema import Document
        
        docs = [
            Document(page_content="Test document one"),
            Document(page_content="Test document two"),
        ]
        
        index = BM25Index()
        index.fit(docs)
        index.save(self.index_path)
        
        # Load the index
        loaded_index = BM25Index.load(self.index_path)
        self.assertIsNotNone(loaded_index)
        self.assertEqual(len(loaded_index.documents), 2)
    
    def test_load_nonexistent(self):
        """Test loading from nonexistent path."""
        loaded = BM25Index.load("/nonexistent/path.pkl")
        self.assertIsNone(loaded)


class TestConfigManager(unittest.TestCase):
    """Test configuration management."""
    
    def setUp(self):
        self.original_config = None
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                import json
                self.original_config = json.load(f)
    
    def tearDown(self):
        if self.original_config:
            save_config(self.original_config)
    
    def test_load_config(self):
        """Test loading configuration."""
        config = load_config()
        self.assertIsInstance(config, dict)
        self.assertIn("model", config)
    
    def test_update_config(self):
        """Test updating configuration."""
        original = load_config()
        update_config({"chunk_size": 500})
        
        updated = load_config()
        self.assertEqual(updated["chunk_size"], 500)
        
        # Restore
        update_config({"chunk_size": original.get("chunk_size", 1000)})
    
    def test_validate_config_valid(self):
        """Test validation with valid config."""
        config = DEFAULT_CONFIG.copy()
        is_valid, errors = validate_config(config)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_config_invalid_chunk_size(self):
        """Test validation with invalid chunk_size."""
        config = DEFAULT_CONFIG.copy()
        config["chunk_size"] = 50  # Too small
        is_valid, errors = validate_config(config)
        self.assertFalse(is_valid)
        self.assertTrue(any("chunk_size" in e for e in errors))
    
    def test_validate_config_invalid_alpha(self):
        """Test validation with invalid hybrid_alpha."""
        config = DEFAULT_CONFIG.copy()
        config["hybrid_alpha"] = 1.5  # Out of range
        is_valid, errors = validate_config(config)
        self.assertFalse(is_valid)
        self.assertTrue(any("hybrid_alpha" in e for e in errors))


class TestDatabase(unittest.TestCase):
    """Test SQLite database operations."""
    
    def setUp(self):
        # Use a separate test database
        import database
        self.original_db_path = database.DB_PATH
        database.DB_PATH = "test_chat_history.db"
        init_db()
    
    def tearDown(self):
        import database
        if os.path.exists("test_chat_history.db"):
            os.remove("test_chat_history.db")
        database.DB_PATH = self.original_db_path
    
    def test_create_session(self):
        """Test creating a chat session."""
        session_id = create_session("Test Session", "test-model")
        self.assertIsInstance(session_id, int)
        self.assertGreater(session_id, 0)
    
    def test_get_session(self):
        """Test retrieving a session."""
        session_id = create_session("Test Session")
        session = get_session(session_id)
        
        self.assertIsNotNone(session)
        self.assertEqual(session["name"], "Test Session")
    
    def test_add_and_get_messages(self):
        """Test adding and retrieving messages."""
        session_id = create_session("Test Session")
        
        add_message(session_id, "user", "Hello!")
        add_message(session_id, "assistant", "Hi there!")
        
        messages = get_messages(session_id)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[1]["role"], "assistant")
    
    def test_format_history(self):
        """Test formatting history for prompts."""
        session_id = create_session("Test Session")
        
        add_message(session_id, "user", "What is Python?")
        add_message(session_id, "assistant", "Python is a programming language.")
        
        history = format_history_for_prompt(session_id)
        self.assertIn("User: What is Python?", history)
        self.assertIn("Assistant: Python is a programming language.", history)
    
    def test_delete_session(self):
        """Test deleting a session."""
        session_id = create_session("To Delete")
        add_message(session_id, "user", "Test message")
        
        result = delete_session(session_id)
        self.assertTrue(result)
        
        session = get_session(session_id)
        self.assertIsNone(session)
    
    def test_rename_session(self):
        """Test renaming a session."""
        session_id = create_session("Original Name")
        
        result = rename_session(session_id, "New Name")
        self.assertTrue(result)
        
        session = get_session(session_id)
        self.assertEqual(session["name"], "New Name")
    
    def test_clear_session_messages(self):
        """Test clearing messages from a session."""
        session_id = create_session("Test Session")
        
        add_message(session_id, "user", "Message 1")
        add_message(session_id, "user", "Message 2")
        
        count = clear_session_messages(session_id)
        self.assertEqual(count, 2)
        
        messages = get_messages(session_id)
        self.assertEqual(len(messages), 0)
    
    def test_get_all_sessions(self):
        """Test retrieving all sessions."""
        create_session("Session 1")
        create_session("Session 2")
        create_session("Session 3")
        
        sessions = get_all_sessions(limit=10)
        self.assertGreaterEqual(len(sessions), 3)


class TestHealthCheck(unittest.TestCase):
    """Test health check functionality."""
    
    def test_check_ollama_health_format(self):
        """Test health check returns proper format."""
        from health_check import check_ollama_health
        
        result = check_ollama_health(timeout=2)
        
        self.assertIn("status", result)
        self.assertIn("available", result)
        self.assertIn("models", result)
        self.assertIsInstance(result["available"], bool)


class TestIngestion(unittest.TestCase):
    """Test document ingestion (requires Ollama running)."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test_doc.txt")
        with open(self.test_file, "w") as f:
            f.write("This is a test document for ingestion testing.\n" * 10)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        # Clean up test index
        if os.path.exists("test_faiss_index"):
            shutil.rmtree("test_faiss_index")
    
    def test_ingest_invalid_file(self):
        """Test ingesting an invalid file."""
        success, msg = ingest_files(["/nonexistent/file.txt"])
        self.assertFalse(success)
        self.assertIn("Error", msg)


if __name__ == '__main__':
    unittest.main(verbosity=2)

