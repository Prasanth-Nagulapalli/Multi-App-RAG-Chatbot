"""
Indexing service for building vector databases.
Handles document loading, chunking, embedding, and Chroma persistence.
"""
import os
from datetime import datetime
from typing import List, Tuple

from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.services.storage import get_files_dir, get_chroma_dir, get_all_file_paths, clear_chroma_dir
from app.db import update_app_status, get_files_for_app

# Embedding model (same as existing config)
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120


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
    print(f"[CHUNK] Created {len(chunks)} chunks from {len(docs)} documents")
    return chunks


def build_index(app_id: str) -> Tuple[int, int]:
    """
    Build/rebuild vector index for an app.
    Returns (num_docs, num_chunks).
    """
    print(f"\n[INDEX] Starting indexing for app: {app_id}")
    
    try:
        # Update status to INDEXING
        update_app_status(app_id, "INDEXING")
        
        # Clear existing Chroma DB (clean rebuild)
        clear_chroma_dir(app_id)
        
        # Load documents
        docs = load_documents(app_id)
        if not docs:
            raise ValueError("No documents could be loaded")
        
        # Chunk documents
        chunks = chunk_documents(docs)
        
        # Create embeddings
        print(f"[EMBED] Creating embeddings with {EMBED_MODEL}...")
        embedding = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
        
        # Build and persist Chroma DB
        chroma_dir = get_chroma_dir(app_id)
        vectordb = Chroma.from_documents(
            documents=chunks,
            embedding=embedding,
            persist_directory=chroma_dir
        )
        
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


def index_exists(app_id: str) -> bool:
    """Check if a Chroma index exists for an app."""
    chroma_dir = get_chroma_dir(app_id)
    # Check if chroma.sqlite3 exists (Chroma's persistence file)
    return os.path.exists(os.path.join(chroma_dir, "chroma.sqlite3"))

