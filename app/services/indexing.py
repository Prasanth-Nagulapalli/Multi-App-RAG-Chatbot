"""
Indexing service for building vector databases.
Handles document loading, chunking, embedding, and Chroma persistence.
"""
import os
from datetime import datetime
from typing import List, Tuple

from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.services.storage import get_files_dir, get_chroma_dir, get_all_file_paths, clear_chroma_dir
from app.db import update_app_status, get_files_for_app

# Embedding model (same as existing config)
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
DEFAULT_COLLECTION = "langchain"
ACTIVE_COLLECTION_FILE = "active_collection.txt"


def load_documents(app_id: str) -> List:
    """Load all documents for an app."""
    file_paths = get_all_file_paths(app_id)
    
    if not file_paths:
        raise ValueError(f"No files found for app '{app_id}'. Please upload files first.")
    
    all_docs = []
    for file_path in file_paths:
        try:
            # Determine loader based on extension
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext in [".txt", ".md"]:
                loader = TextLoader(file_path, encoding="utf-8")
                docs = loader.load()
                all_docs.extend(docs)
                print(f"[LOAD] Loaded: {os.path.basename(file_path)}")
            elif ext == ".pdf":
                # Requires `pypdf` (see requirements.txt)
                loader = PyPDFLoader(file_path)
                docs = loader.load()
                all_docs.extend(docs)
                print(f"[LOAD] Loaded PDF: {os.path.basename(file_path)} ({len(docs)} page(s))")
            else:
                print(f"[SKIP] Skipping unsupported file: {os.path.basename(file_path)}")
                
        except Exception as e:
            print(f"[ERR] Error loading {file_path}: {e}")
    
    return all_docs


def chunk_documents(docs: List) -> List:
    """Split documents into chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )
    chunks = splitter.split_documents(docs)
    # Drop empty chunks (can happen with PDFs that have no extractable text)
    chunks = [c for c in chunks if getattr(c, "page_content", "").strip()]
    print(f"[CHUNK] Created {len(chunks)} chunks from {len(docs)} documents")
    return chunks


def _active_collection_path(app_id: str) -> str:
    return os.path.join(get_chroma_dir(app_id), ACTIVE_COLLECTION_FILE)


def get_active_collection_name(app_id: str) -> str:
    """Return currently active collection for an app."""
    path = _active_collection_path(app_id)
    if not os.path.exists(path):
        return DEFAULT_COLLECTION
    try:
        with open(path, "r", encoding="utf-8") as f:
            name = f.read().strip()
        return name or DEFAULT_COLLECTION
    except Exception:
        return DEFAULT_COLLECTION


def _set_active_collection_name(app_id: str, collection_name: str) -> None:
    os.makedirs(get_chroma_dir(app_id), exist_ok=True)
    with open(_active_collection_path(app_id), "w", encoding="utf-8") as f:
        f.write(collection_name)


def release_vectordb(vectordb) -> None:
    """Best-effort release of Chroma resources (important on Windows file locks)."""
    if vectordb is None:
        return
    try:
        # Persist before shutdown when supported.
        if hasattr(vectordb, "persist"):
            vectordb.persist()
    except Exception:
        pass
    try:
        del vectordb
    except Exception:
        pass


def build_index(app_id: str) -> Tuple[int, int]:
    """
    Build/rebuild vector index for an app.
    Returns (num_docs, num_chunks).
    """
    print(f"\n[INDEX] Starting indexing for app: {app_id}")
    
    vectordb = None
    try:
        # Update status to INDEXING
        update_app_status(app_id, "INDEXING")
        
        # Keep existing files and switch to a fresh collection each rebuild.
        # This avoids Windows file-lock failures while still serving only latest index.
        chroma_dir = get_chroma_dir(app_id)
        os.makedirs(chroma_dir, exist_ok=True)
        
        # Load documents
        docs = load_documents(app_id)
        # Drop docs with no extractable text (common with scanned/image-only PDFs)
        docs = [d for d in docs if getattr(d, "page_content", "").strip()]
        if not docs:
            raise ValueError(
                "No text could be extracted from the uploaded documents. "
                "If you're indexing scanned/image-only PDFs, run OCR first and upload the OCR'd text/PDF."
            )
        
        # Chunk documents
        chunks = chunk_documents(docs)
        if not chunks:
            raise ValueError("No text chunks could be created from the uploaded documents.")
        
        # Create embeddings
        print(f"[EMBED] Creating embeddings with {EMBED_MODEL}...")
        embedding = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
        
        # Build and persist Chroma DB
        collection_name = f"{app_id}_{int(datetime.utcnow().timestamp())}"
        vectordb = Chroma.from_documents(
            documents=chunks,
            embedding=embedding,
            collection_name=collection_name,
            persist_directory=chroma_dir
        )
        _set_active_collection_name(app_id, collection_name)
        
        # Update status to READY
        now = datetime.utcnow().isoformat()
        update_app_status(app_id, "READY", last_indexed_at=now)
        
        print(f"[OK] Index built for app: {app_id}")
        print(f"   Docs: {len(docs)} | Chunks: {len(chunks)}")
        
        return len(docs), len(chunks)
        
    except Exception as e:
        # Update status to FAILED
        update_app_status(app_id, "FAILED")
        print(f"[ERR] Indexing failed for app {app_id}: {e}")
        raise
    finally:
        # Release any open Chroma handles so retraining works reliably on Windows.
        release_vectordb(vectordb)


def index_exists(app_id: str) -> bool:
    """Check if a Chroma index exists for an app."""
    chroma_dir = get_chroma_dir(app_id)
    # Check if chroma.sqlite3 exists (Chroma's persistence file)
    return os.path.exists(os.path.join(chroma_dir, "chroma.sqlite3"))

