# buergerchat

RAG chatbot for German government services (全德國政府服務 RAG chatbot).

## Tech Stack

- **Frontend**: Next.js 14 (TypeScript, App Router)
- **Backend**: FastAPI (Python 3.11)
- **Vector DB**: FAISS
- **Metadata DB**: PostgreSQL
- **Deployment**: Railway

## Project Structure

```
buergerchat/
├── frontend/    # Next.js app
├── backend/     # FastAPI app
└── crawler/     # Government website crawler/scraper
```

## Getting Started

### Backend

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload
```

API available at http://localhost:8000, health check at `/health`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App available at http://localhost:3000.

### Crawler

```bash
cd crawler
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Status

Scaffolding only — no AI/RAG logic implemented yet.
