# Multi-App RAG Chatbot

A multi-tenant RAG (Retrieval-Augmented Generation) chatbot system with local-only storage. Create multiple apps, each with their own document knowledge base.

## Features

- 🏢 **Multi-App Support**: Create separate chatbot apps (e.g., CSS, BES, HR)
- 📄 **Document Upload**: Upload .txt and .md files per app
- 🧠 **Training/Indexing**: Build vector embeddings using sentence-transformers
- 💬 **Embeddable Chat**: Simple chat UI at `/chat?appId=<app>`
- 🎨 **Dashboard UI**: React + Material UI dashboard for management
- 💾 **Local Storage**: All data stored locally (SQLite + file system)

## Project Structure

```
Chat-bot/
├── app/                    # FastAPI backend
│   ├── main.py             # API routes
│   ├── db.py               # SQLite database
│   ├── services/
│   │   ├── storage.py      # File storage
│   │   ├── indexing.py     # Vector indexing
│   │   ├── rag.py          # Chat/retrieval logic
│   │   └── llm.py          # LLM adapter
│   └── templates/
│       └── chat.html       # Embeddable chat UI
├── frontend/               # React dashboard
│   ├── src/
│   │   └── App.js
│   └── package.json
├── storage/                # Local data storage
│   ├── metadata.db         # SQLite database
│   └── apps/
│       └── {appId}/
│           ├── files/      # Uploaded documents
│           └── chroma_db/  # Vector store
├── requirements.txt
└── README.md
```

## Quick Start

### 1. Setup Python Environment

```bash
cd Chat-bot

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your OpenAI API key (optional)
# The system works without it using a mock LLM
```

### 3. Start the Backend

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### 4. Start the Frontend (Optional)

```bash
cd frontend
npm install
npm start
```

Dashboard will be at `http://localhost:3000`

## API Usage

### Create an App

```bash
curl -X POST http://localhost:8000/api/apps \
  -H "Content-Type: application/json" \
  -d '{"appId": "css", "name": "CSS System"}'
```

### Upload Files

```bash
curl -X POST http://localhost:8000/api/apps/css/files \
  -F "files=@documents/css_docs.txt" \
  -F "files=@documents/css_guide.md"
```

### Train the App

```bash
curl -X POST http://localhost:8000/api/apps/css/train
```

### Chat

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"appId": "css", "message": "What is CSS?"}'
```

### Open Chat UI

Navigate to: `http://localhost:8000/chat?appId=css`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/api/apps` | Create new app |
| GET | `/api/apps` | List all apps |
| GET | `/api/apps/{appId}` | Get app details |
| DELETE | `/api/apps/{appId}` | Delete app |
| POST | `/api/apps/{appId}/files` | Upload files |
| GET | `/api/apps/{appId}/files` | List files |
| POST | `/api/apps/{appId}/train` | Train/index app |
| POST | `/api/chat` | Send chat message |
| GET | `/chat?appId={appId}` | Embeddable chat UI |

## Configuration

Environment variables (`.env`):

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for GPT-3.5 | No (mock LLM used if missing) |

## Tech Stack

- **Backend**: FastAPI, Uvicorn
- **Database**: SQLite
- **Vector Store**: ChromaDB
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2
- **LLM**: OpenAI GPT-3.5 (or mock fallback)
- **Frontend**: React, Material UI

## Development

### Run Backend with Auto-reload

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### View API Docs

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Extending

### Adding PDF/DOCX Support

In `app/services/indexing.py`, add loaders:

```python
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader

if ext == ".pdf":
    loader = PyPDFLoader(file_path)
elif ext == ".docx":
    loader = Docx2txtLoader(file_path)
```

Update `app/services/storage.py`:

```python
def get_supported_extensions():
    return [".txt", ".md", ".pdf", ".docx"]
```

## License

MIT
