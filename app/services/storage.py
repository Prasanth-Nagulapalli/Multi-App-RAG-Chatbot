"""
Storage service for managing local file storage.
Handles file paths, saving, and hashing.
"""
import os
import hashlib
import shutil
from typing import List

# Base storage directory
STORAGE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage", "apps")


def get_app_root(app_id: str) -> str:
    """Get root directory for an app."""
    return os.path.join(STORAGE_ROOT, app_id)


def get_files_dir(app_id: str) -> str:
    """Get files directory for an app."""
    return os.path.join(get_app_root(app_id), "files")


def get_chroma_dir(app_id: str) -> str:
    """Get Chroma DB directory for an app."""
    return os.path.join(get_app_root(app_id), "chroma_db")


def ensure_app_dirs(app_id: str):
    """Create app directories if they don't exist."""
    os.makedirs(get_files_dir(app_id), exist_ok=True)
    os.makedirs(get_chroma_dir(app_id), exist_ok=True)
    print(f"[DIR] Created directories for app: {app_id}")


def compute_file_hash(content: bytes) -> str:
    """Compute SHA256 hash of file content."""
    return hashlib.sha256(content).hexdigest()


def save_file(app_id: str, filename: str, content: bytes) -> str:
    """
    Save file to app's files directory.
    Returns the full file path.
    """
    ensure_app_dirs(app_id)
    file_path = os.path.join(get_files_dir(app_id), filename)
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    print(f"[SAVE] Saved file: {filename} for app: {app_id}")
    return file_path


def get_all_file_paths(app_id: str) -> List[str]:
    """Get all file paths in app's files directory."""
    files_dir = get_files_dir(app_id)
    if not os.path.exists(files_dir):
        return []
    
    file_paths = []
    for filename in os.listdir(files_dir):
        file_path = os.path.join(files_dir, filename)
        if os.path.isfile(file_path):
            file_paths.append(file_path)
    
    return file_paths


def delete_file(app_id: str, filename: str) -> bool:
    """Delete a specific file."""
    file_path = os.path.join(get_files_dir(app_id), filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"[DEL] Deleted file: {filename} for app: {app_id}")
        return True
    return False


def clear_chroma_dir(app_id: str):
    """Clear the Chroma DB directory (for rebuilding index)."""
    chroma_dir = get_chroma_dir(app_id)
    if os.path.exists(chroma_dir):
        shutil.rmtree(chroma_dir)
        print(f"[DEL] Cleared Chroma DB for app: {app_id}")
    os.makedirs(chroma_dir, exist_ok=True)


def delete_app_storage(app_id: str):
    """Delete all storage for an app."""
    app_root = get_app_root(app_id)
    if os.path.exists(app_root):
        shutil.rmtree(app_root)
        print(f"[DEL] Deleted all storage for app: {app_id}")


def get_supported_extensions() -> List[str]:
    """Get list of supported file extensions."""
    # MVP: txt and md. Structure allows easy addition of pdf, docx later.
    return [".txt", ".md"]


def is_supported_file(filename: str) -> bool:
    """Check if file extension is supported."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in get_supported_extensions()

