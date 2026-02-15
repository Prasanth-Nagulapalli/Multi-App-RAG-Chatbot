"""
SQLite database setup and helpers for multi-app RAG system.
Stores: apps metadata, files metadata, training status.
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "metadata.db")


def get_connection() -> sqlite3.Connection:
    """Get SQLite connection with row factory for dict-like access."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Apps table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS apps (
            app_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'CREATED',
            last_indexed_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    # Files table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            file_hash TEXT,
            uploaded_at TEXT NOT NULL,
            FOREIGN KEY (app_id) REFERENCES apps(app_id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("[OK] Database initialized")


# ============== APP OPERATIONS ==============

def create_app(app_id: str, name: str) -> Dict[str, Any]:
    """Create a new app."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    try:
        cursor.execute(
            "INSERT INTO apps (app_id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (app_id, name, now, now)
        )
        conn.commit()
        return {"app_id": app_id, "name": name, "status": "CREATED", "created_at": now}
    except sqlite3.IntegrityError:
        raise ValueError(f"App '{app_id}' already exists")
    finally:
        conn.close()


def get_app(app_id: str) -> Optional[Dict[str, Any]]:
    """Get app by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM apps WHERE app_id = ?", (app_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_apps() -> List[Dict[str, Any]]:
    """Get all apps."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM apps ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_app_status(app_id: str, status: str, last_indexed_at: Optional[str] = None):
    """Update app training status."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    if last_indexed_at:
        cursor.execute(
            "UPDATE apps SET status = ?, last_indexed_at = ?, updated_at = ? WHERE app_id = ?",
            (status, last_indexed_at, now, app_id)
        )
    else:
        cursor.execute(
            "UPDATE apps SET status = ?, updated_at = ? WHERE app_id = ?",
            (status, now, app_id)
        )
    conn.commit()
    conn.close()


def delete_app(app_id: str):
    """Delete an app and its files from database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM files WHERE app_id = ?", (app_id,))
    cursor.execute("DELETE FROM apps WHERE app_id = ?", (app_id,))
    conn.commit()
    conn.close()


# ============== FILE OPERATIONS ==============

def add_file(app_id: str, filename: str, file_path: str, file_size: int, file_hash: str) -> Dict[str, Any]:
    """Add file metadata."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    cursor.execute(
        "INSERT INTO files (app_id, filename, file_path, file_size, file_hash, uploaded_at) VALUES (?, ?, ?, ?, ?, ?)",
        (app_id, filename, file_path, file_size, file_hash, now)
    )
    file_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {
        "id": file_id,
        "app_id": app_id,
        "filename": filename,
        "file_size": file_size,
        "uploaded_at": now
    }


def get_files_for_app(app_id: str) -> List[Dict[str, Any]]:
    """Get all files for an app."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM files WHERE app_id = ? ORDER BY uploaded_at DESC", (app_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_file(file_id: int):
    """Delete a file record."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
    conn.commit()
    conn.close()


def delete_files_for_app(app_id: str):
    """Delete all file records for an app."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM files WHERE app_id = ?", (app_id,))
    conn.commit()
    conn.close()


# Initialize on import
init_db()

