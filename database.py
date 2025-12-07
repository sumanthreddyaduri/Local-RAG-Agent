"""
Persistent Chat Memory using SQLite
Thread-safe database operations for storing chat history and sessions.
"""

import sqlite3
import threading
from datetime import datetime
from contextlib import contextmanager
import json
import os

DB_PATH = "chat_history.db"

# Thread-local storage for connections
_local = threading.local()
_lock = threading.Lock()


def get_connection():
    """Get a thread-local database connection."""
    if not hasattr(_local, 'connection'):
        _local.connection = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.connection.row_factory = sqlite3.Row
    return _local.connection


@contextmanager
def get_db():
    """Context manager for database operations with automatic commit/rollback."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e


def init_db():
    """Initialize the database schema."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Chat sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                model_used TEXT,
                metadata TEXT DEFAULT '{}'
            )
        ''')
        
        # Chat messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
            )
        ''')
        
        # Indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_created ON chat_messages(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_updated ON chat_sessions(updated_at)')


def create_session(name=None, model_used=None):
    """Create a new chat session."""
    if name is None:
        name = f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    with _lock:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO chat_sessions (name, model_used) VALUES (?, ?)',
                (name, model_used)
            )
            return cursor.lastrowid


def get_session(session_id):
    """Get a session by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM chat_sessions WHERE id = ?', (session_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_sessions(limit=50):
    """Get all sessions, ordered by most recent."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM chat_sessions ORDER BY updated_at DESC LIMIT ?',
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]


def delete_session(session_id):
    """Delete a session and all its messages."""
    with _lock:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM chat_messages WHERE session_id = ?', (session_id,))
            cursor.execute('DELETE FROM chat_sessions WHERE id = ?', (session_id,))
            return cursor.rowcount > 0


def rename_session(session_id, new_name):
    """Rename a session."""
    with _lock:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE chat_sessions SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                (new_name, session_id)
            )
            return cursor.rowcount > 0


def add_message(session_id, role, content, metadata=None):
    """Add a message to a session."""
    if metadata is None:
        metadata = {}
    
    with _lock:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO chat_messages (session_id, role, content, metadata) VALUES (?, ?, ?, ?)',
                (session_id, role, content, json.dumps(metadata))
            )
            # Update session timestamp
            cursor.execute(
                'UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                (session_id,)
            )
            return cursor.lastrowid


def get_messages(session_id, limit=None):
    """Get all messages for a session."""
    with get_db() as conn:
        cursor = conn.cursor()
        if limit:
            cursor.execute(
                'SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC LIMIT ?',
                (session_id, limit)
            )
        else:
            cursor.execute(
                'SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC',
                (session_id,)
            )
        return [dict(row) for row in cursor.fetchall()]


def get_recent_messages(session_id, count=10):
    """Get the most recent N messages for context."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT * FROM (
                SELECT * FROM chat_messages 
                WHERE session_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            ) ORDER BY created_at ASC''',
            (session_id, count)
        )
        return [dict(row) for row in cursor.fetchall()]


def format_history_for_prompt(session_id, count=10):
    """Format recent messages as a string for LLM prompts."""
    messages = get_recent_messages(session_id, count)
    history_lines = []
    for msg in messages:
        role = "User" if msg['role'] == 'user' else "Assistant"
        history_lines.append(f"{role}: {msg['content']}")
    return "\n".join(history_lines)


def clear_session_messages(session_id):
    """Clear all messages in a session without deleting the session."""
    with _lock:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM chat_messages WHERE session_id = ?', (session_id,))
            return cursor.rowcount


def get_or_create_default_session():
    """Get the most recent session or create a new one if none exist."""
    sessions = get_all_sessions(limit=1)
    if sessions:
        return sessions[0]['id']
    return create_session("Default Session")


def search_messages(query, limit=20):
    """Search messages across all sessions."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT m.*, s.name as session_name 
               FROM chat_messages m 
               JOIN chat_sessions s ON m.session_id = s.id
               WHERE m.content LIKE ? 
               ORDER BY m.created_at DESC 
               LIMIT ?''',
            (f'%{query}%', limit)
        )
        return [dict(row) for row in cursor.fetchall()]


# Initialize database on module import
init_db()
