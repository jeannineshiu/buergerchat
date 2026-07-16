# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

buergerchat is a RAG chatbot for German government services (全德國政府服務 RAG chatbot). It is a monorepo with three independent modules, each with its own dependency set; git history is shared at the repo root only. Crawler and backend deliberately do not import from each other — they agree on schemas (JSONL fields, the `chunks` table) instead of sharing code.

**Positioning:** translate official German documents into plain language (einfache Sprache), always citing original sources, so anyone can understand their rights. Three MVP themes, in priority order: (1) Bürgergeld / Neue Grundsicherung, (2) Kindergeld, (3) finding the right Behörde. Answers should be actionable (eligibility, steps, responsible authority) — not just informative.

**Current status:** crawler, backend RAG pipeline, Behörden-Finder (live PVOG lookup), and frontend chat UI are working end-to-end locally. Not yet done: Postgres (using SQLite locally), Railway deployment, Daytona crawler sandboxes, weekly re-crawl cron, tests.

## Structure

```
buergerchat/
├── frontend/    # Next.js (TypeScript, App Router) — chat UI
├── backend/     # FastAPI (Python 3.11) — RAG chat API
├── crawler/     # Crawlers + index build for German government websites
└── data/        # Built FAISS index + SQLite metadata DB (gitignored, regenerable)
```

- `backend/main.py` — FastAPI entrypoint; `POST /chat` (request: `{message, language="de", history=[]}` where history items are `{role: user|assistant, content}`; response: `{answer, sources: [{title, url}], topic}`; 503 `{error}` while the index is missing), `GET /health` (always 200: `{status: ok|degraded, index: loaded|missing}` — degraded means the volume isn't populated yet), `POST /feedback/message` (thumbs per answer) + `POST /feedback/session` (1–5 stars per conversation) → `feedback.db`, a **separate** sqlite file in `DATA_DIR` (`FEEDBACK_DATABASE_URL` to override) — never metadata.db, which the index upload replaces wholesale. CORS allows `http://localhost:3000` + `FRONTEND_ORIGIN`. Loads `backend/.env` at import time. Falls back to `history` for topic/authority-intent/PLZ so a bare-PLZ follow-up ("10115") works.
- `backend/rag.py` — `RAGPipeline`: loads the FAISS index read-only and **lazily** (first query or `/health`, not import — the app must boot with an empty volume; raises `IndexNotReadyError` → /chat 503); query → embed (`text-embedding-3-small`) → top-5 cosine search → metadata lookup → answer via `gpt-5.4-mini` (`CHAT_MODEL` env to override; 4o-mini code-switched German into zh-Hans answers). Optionally injects a `BehoerdeResult` as an extra context block + first source, and carries prompt directives for ask-for-PLZ / authority-not-found (must not invent addresses).
- `backend/router.py` — `QueryRouter`, rule-based topic classification (buergergeld / kindergeld / arbeitslos / familie-und-kinder / allgemein), plus `wants_authority()` (keyword intent: user asks which Behörde is responsible) and `extract_plz()`.
- `backend/behoerde.py` — `BehoerdeFinder`: live lookup of the zuständige Stelle via the public PVOG Suchdienst API (no API key). Chain: PLZ → ARS candidates (exact → Kreis → Land level, since e.g. Berlin registers data at city level) → Leistung search (topic-specific query terms, else stopword-stripped user message) → organisation units (role 01 preferred) → detail with address. Land/Kommune Leistungen win over federal ones (federal = hotline fallback). Any failure returns `None`; /chat degrades gracefully.
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

```bash
cd frontend
npm install
npm run dev     # http://localhost:3000, expects backend on :8000 (NEXT_PUBLIC_API_URL to override)
```

No test suite exists yet for any module; `npm run build` doubles as the frontend typecheck.

## Architecture notes

- **Vector DB is FAISS** (`IndexIDMap(IndexFlatIP)` over L2-normalized vectors = cosine). Index *building* (crawler's job) and index *loading* (backend's job, read-only at startup) stay separate — FAISS has no multi-process story, and under Railway each worker/replica loads the index independently.
- **Metadata DB**: SQLite (`sqlite:///data/metadata.db`) for local dev; production target is Railway PostgreSQL. Everything goes through SQLAlchemy, so switching is a `DATABASE_URL` change only. Metadata only (URLs, chunk text, topics, timestamps) — no vectors.
- **Paths**: always resolve relative to the repo root / `__file__`, never cwd. Relative sqlite/FAISS/output paths in env vars are anchored to the repo root by the code. (cwd-relative output paths silently wrote to `crawler/crawler/output/` twice before this convention.)
- **Deployment: Railway, two Docker services.** Each service's Root Directory (dashboard setting) is `backend` / `frontend`; each directory has its own `Dockerfile` + `railway.toml` (Railway config-as-code is per-service — one root file for both is not supported). The `data/` artifacts live on a **Railway volume mounted at `/data`** on the backend (`DATA_DIR` env, default `/data` in the image, `data` locally; relative values repo-root-anchored). The volume is populated by uploading locally built artifacts via `scripts/upload-index.sh` (wraps `railway volume files upload`; needs `railway login` + `railway link` once). No restart needed after upload — the index loads lazily. Frontend is a Next.js `standalone` build; `NEXT_PUBLIC_API_URL` is a **build-time** arg and must be the backend's **public** domain (the browser calls it — `.railway.internal` is unreachable from clients). Backend CORS: set `FRONTEND_ORIGIN` to the deployed frontend origin.
- Env vars live in `backend/.env` (`DATABASE_URL`, `DATA_DIR`, optional `FAISS_INDEX_PATH` override, `OPENAI_API_KEY`, production `FRONTEND_ORIGIN`); `crawler/build_index.py` also reads `backend/.env`.
- **Behörden-Finder is a live API integration, not crawled data**: responsibility depends on the user's location (~11k Kommunen), so `backend/behoerde.py` queries the official PVOG Suchdienst (`https://pvog.fitko.net/suchdienst/api`, public, no key) per request. Nothing PVOG goes into the FAISS index.
- **Bürgergeld → Grundsicherungsgeld rename** (effective 2026-07-01): official sites are mid-transition, both terms must stay in crawl keywords and be understood at query time (also in `behoerde.py`'s `TOPIC_QUERIES`, which tries both names against PVOG).
