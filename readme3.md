# Multi-App RAG Chatbot - Quick Start Guide

A multi-tenant RAG chatbot where you can create multiple apps, each with their own document knowledge base.

---

## Prerequisites

- Python 3.10+
- Node.js 18+ (for React dashboard, optional)
- OpenAI API Key (optional - works with mock LLM without it)

---

## Step 1: Setup Python Environment

```bash
# Navigate to project folder
cd C:\Users\prasa\Desktop\Chat-bot

# Create virtual environment (if not exists)
python -m venv venv

# Activate virtual environment (Windows)
.\venv\Scripts\Activate.ps1

# Or for Command Prompt
venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt
```

---

## Step 2: Configure Environment (Optional)

If you have an OpenAI API key, create a `.env` file:

```
OPENAI_API_KEY=your_api_key_here
```

> **Note:** The app works without an API key using a mock LLM that returns relevant document chunks.

---

## Step 3: Start the Backend Server

```bash
# Make sure you're in the project folder with venv activated
cd C:\Users\prasa\Desktop\Chat-bot
.\venv\Scripts\Activate.ps1

# Start the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Started reloader process
```

---

## Step 4: Use the App

### Option A: Use the Chat UI (Easiest)

1. Open browser: **http://localhost:8000/chat?appId=css**
2. Start chatting!

### Option B: Use the API Documentation

1. Open browser: **http://localhost:8000/docs**
2. Interactive Swagger UI to test all endpoints

### Option C: Use the React Dashboard

```bash
# Open a NEW terminal
cd C:\Users\prasa\Desktop\Chat-bot\frontend

# Install dependencies (first time only)
npm install

# Start React app
npm start
```

Dashboard opens at: **http://localhost:3000**

---

## Step 5: Create Your Own App

### Using API (cURL or PowerShell):

```powershell
# 1. Create an app
$body = '{"appId": "myapp", "name": "My Custom App"}'
Invoke-WebRequest -Uri "http://localhost:8000/api/apps" -Method POST -Body $body -ContentType "application/json"

# 2. Upload files
# Use the dashboard or Swagger UI at /docs

# 3. Train the app
Invoke-WebRequest -Uri "http://localhost:8000/api/apps/myapp/train" -Method POST

# 4. Chat
$chat = '{"appId": "myapp", "message": "What is this about?"}'
Invoke-WebRequest -Uri "http://localhost:8000/api/chat" -Method POST -Body $chat -ContentType "application/json"
```

### Using Dashboard:

1. Go to http://localhost:3000
2. Click "Create App"
3. Enter App ID (e.g., `hr-docs`) and Name (e.g., `HR Documents`)
4. Click "Files" → Upload your .txt or .md files
5. Click "Train"
6. Click "Chat" to open the chat interface

---

## API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/docs` | Swagger API documentation |
| POST | `/api/apps` | Create new app |
| GET | `/api/apps` | List all apps |
| GET | `/api/apps/{appId}` | Get app details |
| DELETE | `/api/apps/{appId}` | Delete app |
| POST | `/api/apps/{appId}/files` | Upload files (.txt, .md, .pdf) |
| GET | `/api/apps/{appId}/files` | List uploaded files |
| POST | `/api/apps/{appId}/train` | Train/index the app |
| POST | `/api/chat` | Send chat message |
| GET | `/chat?appId={appId}` | Embeddable chat UI |

---

## Project Structure

```
Chat-bot/
├── app/                      # FastAPI Backend
│   ├── main.py               # API routes
│   ├── db.py                 # SQLite database
│   ├── services/
│   │   ├── storage.py        # File storage
│   │   ├── indexing.py       # Vector indexing
│   │   ├── rag.py            # Chat/retrieval
│   │   └── llm.py            # LLM adapter
│   └── templates/
│       └── chat.html         # Embeddable chat UI
│
├── frontend/                 # React Dashboard
│   ├── src/App.js
│   └── package.json
│
├── storage/                  # Local Data (auto-created)
│   ├── metadata.db           # SQLite database
│   └── apps/{appId}/
│       ├── files/            # Uploaded documents
│       └── chroma_db/        # Vector store
│
├── requirements.txt
└── readme3.md                # This file
```

---

## Troubleshooting

### Server won't start?
```bash
# Make sure venv is activated
.\venv\Scripts\Activate.ps1

# Check if port 8000 is in use
netstat -ano | findstr :8000
```

### Chat returns empty?
- Make sure you've uploaded files AND clicked "Train"
- Check app status is "READY" in the dashboard

### Unicode errors on Windows?
- The code has been updated to avoid emojis
- If issues persist, set: `$env:PYTHONIOENCODING = "utf-8"`

---

## Quick Test Commands

```powershell
# Test server is running
Invoke-WebRequest http://localhost:8000/

# List all apps
Invoke-WebRequest http://localhost:8000/api/apps

# Chat with CSS app
$body = '{"appId": "css", "message": "What is CSS?"}'
Invoke-WebRequest -Uri "http://localhost:8000/api/chat" -Method POST -Body $body -ContentType "application/json"
```

---

## URLs at a Glance

| URL | Description |
|-----|-------------|
| http://localhost:8000 | API root |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/chat?appId=css | Chat with CSS app |
| http://localhost:3000 | React Dashboard |

---

**Happy Chatting! 🤖**

