"""
FastAPI application for Multi-App RAG Chatbot.
Provides REST API endpoints for app management, file upload, training, and chat.
"""
import os
import re
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

from app import db
from app.services import storage, indexing, rag

# ============== FastAPI App Setup ==============

app = FastAPI(
    title="Multi-App RAG Chatbot",
    description="A multi-tenant RAG chatbot with local storage",
    version="1.0.0"
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Pydantic Models ==============

class CreateAppRequest(BaseModel):
    appId: str
    name: str
    
    @field_validator("appId")
    @classmethod
    def validate_app_id(cls, v):
        if not re.match(r"^[a-zA-Z0-9-]+$", v):
            raise ValueError("appId must contain only letters, numbers, and dashes")
        if len(v) < 2 or len(v) > 50:
            raise ValueError("appId must be between 2 and 50 characters")
        return v.lower()


class ChatRequest(BaseModel):
    appId: str
    message: str
    
    @field_validator("message")
    @classmethod
    def validate_message(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Message cannot be empty")
        return v.strip()


class AppResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class AppsListResponse(BaseModel):
    success: bool
    data: List[dict]


class ChatResponse(BaseModel):
    success: bool
    answer: Optional[str] = None
    sources: List[str] = []
    error: Optional[str] = None


# ============== Health Check ==============

@app.get("/")
async def root():
    return {"message": "Multi-App RAG Chatbot API", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ============== App Management ==============

@app.post("/api/apps", response_model=AppResponse)
async def create_app(request: CreateAppRequest):
    """Create a new app."""
    try:
        app_data = db.create_app(request.appId, request.name)
        storage.ensure_app_dirs(request.appId)
        print(f"[OK] Created app: {request.appId}")
        return AppResponse(success=True, data=app_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/apps", response_model=AppsListResponse)
async def list_apps():
    """List all apps."""
    apps = db.get_all_apps()
    return AppsListResponse(success=True, data=apps)


@app.get("/api/apps/{app_id}", response_model=AppResponse)
async def get_app(app_id: str):
    """Get app details."""
    app_data = db.get_app(app_id)
    if not app_data:
        raise HTTPException(status_code=404, detail=f"App '{app_id}' not found")
    
    # Add file count
    files = db.get_files_for_app(app_id)
    app_data["file_count"] = len(files)
    
    return AppResponse(success=True, data=app_data)


@app.delete("/api/apps/{app_id}", response_model=AppResponse)
async def delete_app(app_id: str):
    """Delete an app and all its data."""
    app_data = db.get_app(app_id)
    if not app_data:
        raise HTTPException(status_code=404, detail=f"App '{app_id}' not found")
    
    # Delete storage
    storage.delete_app_storage(app_id)
    
    # Delete from database
    db.delete_app(app_id)
    
    print(f"[DEL] Deleted app: {app_id}")
    return AppResponse(success=True, data={"message": f"App '{app_id}' deleted"})


# ============== File Upload ==============

@app.post("/api/apps/{app_id}/files", response_model=AppResponse)
async def upload_files(app_id: str, files: List[UploadFile] = File(...)):
    """Upload files to an app."""
    # Validate app exists
    app_data = db.get_app(app_id)
    if not app_data:
        raise HTTPException(status_code=404, detail=f"App '{app_id}' not found")
    
    uploaded = []
    errors = []
    
    for file in files:
        # Validate file extension
        if not storage.is_supported_file(file.filename):
            errors.append(f"Unsupported file type: {file.filename}")
            continue
        
        try:
            # Read file content
            content = await file.read()
            
            # Compute hash
            file_hash = storage.compute_file_hash(content)
            
            # Save file
            file_path = storage.save_file(app_id, file.filename, content)
            
            # Add to database
            file_data = db.add_file(
                app_id=app_id,
                filename=file.filename,
                file_path=file_path,
                file_size=len(content),
                file_hash=file_hash
            )
            
            uploaded.append(file_data)
            
        except Exception as e:
            errors.append(f"Error uploading {file.filename}: {str(e)}")
    
    # Update app status to indicate new files (needs retraining)
    if uploaded:
        db.update_app_status(app_id, "FILES_UPDATED")
    
    return AppResponse(
        success=True,
        data={
            "uploaded": uploaded,
            "errors": errors,
            "message": f"Uploaded {len(uploaded)} file(s)"
        }
    )


@app.get("/api/apps/{app_id}/files")
async def list_files(app_id: str):
    """List files for an app."""
    app_data = db.get_app(app_id)
    if not app_data:
        raise HTTPException(status_code=404, detail=f"App '{app_id}' not found")
    
    files = db.get_files_for_app(app_id)
    return {"success": True, "data": files}


# ============== Training / Indexing ==============

@app.post("/api/apps/{app_id}/train", response_model=AppResponse)
async def train_app(app_id: str):
    """Train (index) an app's documents."""
    # Validate app exists
    app_data = db.get_app(app_id)
    if not app_data:
        raise HTTPException(status_code=404, detail=f"App '{app_id}' not found")
    
    # Check if files exist
    files = db.get_files_for_app(app_id)
    if not files:
        raise HTTPException(
            status_code=400,
            detail=f"No files uploaded for app '{app_id}'. Please upload files first."
        )
    
    try:
        num_docs, num_chunks = indexing.build_index(app_id)
        return AppResponse(
            success=True,
            data={
                "message": f"Training complete for app '{app_id}'",
                "documents": num_docs,
                "chunks": num_chunks,
                "status": "READY"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== Chat ==============

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a chat message to an app's RAG system."""
    result = rag.chat(request.appId, request.message)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return ChatResponse(
        success=True,
        answer=result["answer"],
        sources=result["sources"]
    )


# ============== Embeddable Chat UI ==============

@app.get("/chat", response_class=HTMLResponse)
async def chat_ui(appId: str = Query(..., description="App ID to chat with")):
    """Serve the embeddable chat UI."""
    # Validate app exists
    app_data = db.get_app(appId)
    if not app_data:
        return HTMLResponse(
            content=f"<html><body><h1>Error</h1><p>App '{appId}' not found</p></body></html>",
            status_code=404
        )
    
    # Read and return the chat template
    template_path = os.path.join(os.path.dirname(__file__), "templates", "chat.html")
    
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # Replace placeholders
        html_content = html_content.replace("{{APP_ID}}", appId)
        html_content = html_content.replace("{{APP_NAME}}", app_data.get("name", appId))
        
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(
            content="<html><body><h1>Error</h1><p>Chat template not found</p></body></html>",
            status_code=500
        )


# ============== Startup Event ==============

@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    print("[START] Starting Multi-App RAG Chatbot API...")
    db.init_db()
    print("[OK] API ready!")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

