# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

buergerchat is a RAG chatbot for German government services (全德國政府服務 RAG chatbot). It is a monorepo with three independent modules, each with its own dependency set; git history is shared at the repo root only. Crawler and backend deliberately do not import from each other — they agree on schemas (JSONL fields, the `chunks` table) instead of sharing code.

**Positioning:** translate official German documents into plain language (einfache Sprache), always citing original sources, so anyone can understand their rights. Three MVP themes, in priority order: (1) Bürgergeld / Neue Grundsicherung, (2) Kindergeld, (3) finding the right Behörde. Answers should be actionable (eligibility, steps, responsible authority) — not just informative.

**Current status:** crawler and backend RAG pipeline are working end-to-end locally. Frontend is not yet initialized. Not yet done: Postgres (using SQLite locally), Railway deployment, Daytona crawler sandboxes, weekly re-crawl cron, tests.

## Structure

```
buergerchat/
├── frontend/    # Next.js 14 (TypeScript, App Router) — not yet initialized
├── backend/     # FastAPI (Python 3.11) — RAG chat API
├── crawler/     # Crawlers + index build for German government websites
└── data/        # Built FAISS index + SQLite metadata DB (gitignored, regenerable)
```

- `backend/main.py` — FastAPI entrypoint; `POST /chat` (request: `{message, language="de"}`, response: `{answer, sources: [{title, url}], topic}`), `GET /health`. CORS allows `http://localhost:3000`. Loads `backend/.env` at import time.
- `backend/rag.py` — `RAGPipeline`: loads FAISS index read-only at startup; query → embed (`text-embedding-3-small`) → top-5 cosine search → metadata lookup → answer via `gpt-4o-mini`.
- `backend/router.py` — `QueryRouter`, rule-based topic classification (buergergeld / kindergeld / arbeitslos / familie-und-kinder / allgemein).
- `backend/app/db.py`, `backend/app/models.py` — SQLAlchemy engine + `Chunk` model (`chunks` table; `id` doubles as the FAISS vector ID).
- `crawler/arbeitsagentur_crawler.py` — sitemap-driven crawl of arbeitsagentur.de, topic-filtered by URL keywords → `crawler/output/arbeitsagentur.jsonl`. Incremental: re-running skips already-crawled URLs and appends.
- `crawler/gesetze_crawler.py` — 5 laws (SGB I/II/VIII/X, BKGG) from gesetze-im-internet.de, one record per § section → `crawler/output/gesetze.jsonl`. Site pages are ISO-8859-1, not UTF-8.
- `crawler/build_index.py` — merge JSONLs → chunk (800 chars / 100 overlap) → OpenAI embeddings → writes `data/faiss_index.bin` + `data/metadata.db` (drop-and-recreate, full re-embed each run).
- `crawler/main.py` — placeholder, unused.

JSONL record schema: `{url, title, content, topic, crawled_at}` (+ `law` for gesetze). Crawlers use User-Agent `BuergerChat-Bot/1.0 (educational project)` and 1–2 s sleep between requests.

## Environment & commands

One shared **conda env** for backend and crawler (not venv — the user chose conda; local machine has no python3.11 outside conda):

```bash
conda activate buergerchat        # Python 3.11
pip install -r backend/requirements.txt -r crawler/requirements.txt
```

`numpy<2` is required — `faiss-cpu==1.8.0` segfaults/ImportErrors under NumPy 2.x.

### Backend

```bash
cd backend
cp .env.example .env   # fill in OPENAI_API_KEY
uvicorn main:app --reload
```

API at `http://localhost:8000`. Startup requires `OPENAI_API_KEY` set and `data/faiss_index.bin` present (run the crawler + build_index first), otherwise import fails.

### Crawler / index build

```bash
cd crawler
python arbeitsagentur_crawler.py   # ~45 min full crawl (rate-limited)
python gesetze_crawler.py          # seconds (5 requests)
python build_index.py              # merge + chunk + embed + write data/
```

### Frontend

Not yet initialized. To scaffold:

```bash
cd frontend
npx create-next-app@latest . --typescript --app --tailwind --eslint --src-dir --import-alias "@/*"
```

No test suite, linter, or build step exists yet for any module.

## Architecture notes

- **Vector DB is FAISS** (`IndexIDMap(IndexFlatIP)` over L2-normalized vectors = cosine). Index *building* (crawler's job) and index *loading* (backend's job, read-only at startup) stay separate — FAISS has no multi-process story, and under Railway each worker/replica loads the index independently.
- **Metadata DB**: SQLite (`sqlite:///data/metadata.db`) for local dev; production target is Railway PostgreSQL. Everything goes through SQLAlchemy, so switching is a `DATABASE_URL` change only. Metadata only (URLs, chunk text, topics, timestamps) — no vectors.
- **Paths**: always resolve relative to the repo root / `__file__`, never cwd. Relative sqlite/FAISS/output paths in env vars are anchored to the repo root by the code. (cwd-relative output paths silently wrote to `crawler/crawler/output/` twice before this convention.)
- **Deployment target is Railway.** Open question: how the ~130 MB `data/` artifacts get to the backend service (volume vs. object storage vs. rebuild on deploy).
- Env vars live in `backend/.env` (`DATABASE_URL`, `FAISS_INDEX_PATH`, `OPENAI_API_KEY`); `crawler/build_index.py` also reads `backend/.env`.
- **Bürgergeld → Grundsicherungsgeld rename** (effective 2026-07-01): official sites are mid-transition, both terms must stay in crawl keywords and be understood at query time.
