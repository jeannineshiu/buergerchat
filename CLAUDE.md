# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

buergerchat is a RAG chatbot for German government services (全德國政府服務 RAG chatbot). It is a monorepo with three independent modules, each with its own dependency set; git history is shared at the repo root only. Crawler and backend deliberately do not import from each other — they agree on schemas (JSONL fields, the `chunks` table) instead of sharing code.

**Positioning:** translate official German documents into plain language (einfache Sprache), always citing original sources, so anyone can understand their rights. Three MVP themes, in priority order: (1) Bürgergeld / Neue Grundsicherung, (2) Kindergeld, (3) finding the right Behörde. Knowledge base since 2026-07 also covers Rente, Wohngeld, Steuer-ID/Steuern, Aufenthalt/Einbürgerung and deeper family benefits (topics chosen from MBE migration-counseling demand reports). Answers should be actionable (eligibility, steps, responsible authority) — not just informative.

**Current status:** crawler, backend RAG pipeline, Behörden-Finder (live PVOG lookup), and frontend chat UI are working end-to-end locally; tests, golden-question evals (`backend/evals/`) and the weekly re-crawl exist. The re-crawl runs in a **Daytona sandbox** (`scripts/daytona_recrawl.py`; crawl state + built index persist in the Daytona volume `buergerchat-crawl`; `--download` pulls the index locally), triggered by the thin `.github/workflows/weekly-crawl.yml` cron (repo secrets: `DAYTONA_API_KEY`, `OPENAI_API_KEY`). The backend is **deployed and live on Railway** at `https://buergerchat-production.up.railway.app` (project `lively-recreation`, service `buergerchat`, volume `buergerchat-volume` mounted at `/data`). Not yet done: Postgres (still SQLite, in production too), automatic volume→Railway upload after a crawl — shipping a fresh index is still the manual `--download` → `scripts/upload-index.sh` → **redeploy** sequence.

## Structure

```
buergerchat/
├── frontend/    # Next.js (TypeScript, App Router) — chat UI
├── backend/     # FastAPI (Python 3.11) — RAG chat API
├── crawler/     # Crawlers + index build for German government websites
└── data/        # Built FAISS index + SQLite metadata DB (gitignored, regenerable)
```

- `backend/main.py` — FastAPI entrypoint; `POST /chat` (request: `{message, language="de", history=[]}` where history items are `{role: user|assistant, content}`; response: `{answer, sources: [{title, url}], topic}`; 503 `{error}` while the index is missing), `GET /health` (always 200: `{status: ok|degraded, index: loaded|missing}` — degraded means the volume isn't populated yet), `POST /feedback/message` (thumbs per answer) + `POST /feedback/session` (1–5 stars per conversation) → `feedback.db`, a **separate** sqlite file in `DATA_DIR` (`FEEDBACK_DATABASE_URL` to override) — never metadata.db, which the index upload replaces wholesale. CORS allows `http://localhost:3000` + `FRONTEND_ORIGIN`. Rate-limited per client IP via slowapi (`/chat` 10/min, feedback 30/min; key = first X-Forwarded-For hop — Railway's edge sets it) and request sizes are capped (message 2000 chars, history 20×8000) so the endpoint can't be used as a free unmetered LLM proxy; pair with a hard budget limit in the OpenAI dashboard. Rate-limit counts live in-process memory by default — correct with today's single Railway replica, but each additional replica would count independently and silently multiply every limit. Set `RATELIMIT_STORAGE_URI` (e.g. `redis://…`; `redis` package already pinned) before scaling replicas — main.py logs a startup warning if `FRONTEND_ORIGIN` (production) is set without it. Loads `backend/.env` at import time. Falls back to `history` for topic/authority-intent/PLZ so a bare-PLZ follow-up ("10115") works.
- `backend/rag.py` — `RAGPipeline`: loads the FAISS index read-only and **lazily** (first query or `/health`, not import — the app must boot with an empty volume; raises `IndexNotReadyError` → /chat 503); query → embed (`text-embedding-3-small`) → top-5 cosine search → metadata lookup → answer via `gpt-5.5`. With `RERANK=1` (**default off in code, but set in production** since 2026-08-09), the vector search widens to `CANDIDATE_K=30` and an LLM rerank appends up to `RERANK_EXTRA_K=3` picks *after* the untouched vector top-5 (union, not swap — swap mode was zero-sum and net-hurt recall; union took golden retrieval recall de/en/zh-Hant to 100/100/100%). Costs one extra chat call per query. (`CHAT_MODEL` env to override; see the model-history comment in rag.py — 4o-mini code-switched, 5.4-mini ignored the no-offer style rules, and the whole `*-chat-latest` line was deprecated by OpenAI on 2026-09-09, taking /chat down with 404s until the default moved to gpt-5.5). A regex guard retries once when the answer leaks a script no answer language uses (both 5.x models occasionally emit Thai ย้อนหลัง for "retroactive" in Chinese answers). Optionally injects a `BehoerdeResult` as an extra context block + first source, and carries prompt directives for ask-for-PLZ / authority-not-found (must not invent addresses).
- `backend/router.py` — `QueryRouter`, rule-based topic classification (buergergeld / kindergeld / arbeitslos / familie-und-kinder / rente / wohngeld / steuern / aufenthalt / allgemein), plus `wants_authority()` (keyword intent: user asks which Behörde is responsible) and `extract_plz()`.
- `backend/behoerde.py` — `BehoerdeFinder`: live lookup of the zuständige Stelle via the public PVOG Suchdienst API (no API key). Chain: PLZ → ARS candidates (exact → Kreis → Land level, since e.g. Berlin registers data at city level) → Leistung search (topic-specific query terms, else stopword-stripped user message) → organisation units (role 01 preferred) → detail with address. Land/Kommune Leistungen win over federal ones (federal = hotline fallback). **PVOG never answers "no match"** — it always returns its nearest rows, so every hit is checked against the query's most specific word (`key_terms()` / `is_relevant()`, umlaut-folded substring match) before it is offered: without that, "Which office is responsible? 10115" was answered with the BaFin arbitration board in Bonn, address included. A query with no specific word left ("Wo ist das Amt?") is not searched at all. The same search is retried with the key word alone, because surrounding words wreck PVOG's ranking ("bekomme Personalausweis" → one unrelated certificate service; "Personalausweis" → the Bürgeramt service). Units with no address, phone or website are skipped (a Hamburg entry named "Informationen" used to beat the Familienkasse by being local), and placeholder addresses (zip "-----") are dropped. Any failure returns `None`; /chat degrades gracefully — and when the lookup fails with topic `allgemein`, main.py sets `ask_for_topic` so the answer asks what the matter is about instead of naming a guess. Known gap: inside a city-state the district match is a plain substring, so Berlin "Mitte" also matches "Bürgeramt Helle Mitte" (Marzahn-Hellersdorf).
- `backend/app/db.py`, `backend/app/models.py` — SQLAlchemy engine + `Chunk` model (`chunks` table; `id` doubles as the FAISS vector ID).
- `crawler/arbeitsagentur_crawler.py` — sitemap-driven crawl of arbeitsagentur.de, topic-filtered by URL keywords → `crawler/output/arbeitsagentur.jsonl`. Incremental: re-running skips already-crawled URLs and appends.
- `crawler/gesetze_crawler.py` — 9 laws (SGB I/II/VI/VIII/X/XII, BKGG, WoGG, AufenthG) from gesetze-im-internet.de, one record per § section → `crawler/output/gesetze.jsonl`. Site pages are ISO-8859-1, not UTF-8.
- `crawler/portal_crawler.py` — one configurable crawler for the portal sites → `crawler/output/portal_<site>.jsonl`: familienportal.de (family benefits), bzst.de (Steuer-ID/taxes; **robots Crawl-delay 30s**, only `/DE/Privatpersonen/`), deutsche-rentenversicherung.de (Rente; Crawl-delay 12s), bmwsb.bund.de (Wohngeld), bamf.de (Aufenthalt; no sitemap → BFS restricted to `/DE/Themen/`, depth ≤ 3), service.berlin.de (~600 Berlin Dienstleistungen; BFS from the German index, numeric detail pages only, topic `berlin`). Sitemap-driven otherwise, incremental like the arbeitsagentur crawler. `python portal_crawler.py [site ...] [--limit N]`. Uses the lxml parser — service.berlin.de markup breaks bs4's html.parser (loses `<body>`).
- `crawler/build_index.py` — merge JSONLs → chunk (800 chars / 100 overlap) → OpenAI embeddings → writes `data/faiss_index.bin` + `data/metadata.db` (drop-and-recreate, full re-embed each run).
- `crawler/main.py` — placeholder, unused.

JSONL record schema: `{url, title, content, topic, crawled_at}` (+ `law` for gesetze). Crawlers use User-Agent `BuergerChat-Bot/1.0 (educational project)` and 1–2 s sleep between requests.

## Environment & commands

One shared **conda env** for backend and crawler (not venv — the user chose conda; local machine has no python3.11 outside conda):

```bash
conda activate buergerchat        # Python 3.11
pip install -r backend/requirements.txt -r crawler/requirements.txt
```

backend and crawler pin the same `faiss-cpu`/`numpy` versions (currently 1.14.3 / 2.4.6) — they must move together since both land in this one shared env; a mismatch between the two files' pins makes `pip install -r backend/requirements.txt -r crawler/requirements.txt` fail with a dependency conflict (numpy<2 was required for the older faiss-cpu==1.8.0, which segfaulted/ImportErrored under NumPy 2.x; that's resolved as of faiss-cpu 1.14.3).

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
python gesetze_crawler.py          # seconds (9 requests)
python portal_crawler.py           # ~1.5-2 h all five portals (bzst's 30s crawl-delay dominates)
python build_index.py              # merge + chunk + embed + write data/
```

### Frontend

```bash
cd frontend
npm install
npm run dev     # http://localhost:3000, expects backend on :8000 (NEXT_PUBLIC_API_URL to override)
```

### Tests

```bash
cd backend && pip install -r requirements-dev.txt && python -m pytest tests/   # 85 tests
cd crawler && python -m pytest tests/                                          # 21 tests
cd frontend && npm test                                                        # 13 tests (vitest)
```

**Evals (online, cost money — don't run casually):** `cd backend && python evals/run_evals.py` = retrieval recall@5 per language against the real index + OpenAI embeddings (~$0.001); `--answers [--limit N]` adds real chat completions. Golden set in `backend/evals/golden.jsonl` — markers must exist in metadata.db (topic + all markers in one chunk), facts must be language-neutral (digits / German proper nouns). Baseline 2026-07-18 (stale corpus, no query translation): retrieval de 84% / en 95% / zh-Hant 63%; answers de 88% / en 88% / zh-Hant 62%; every answer failure tracked a retrieval miss. 2026-07-19, after re-crawl + query→German translation (all queries except de/en — embedding aligns ONLY German and English well with the German corpus; tr/pl/vi/id sat at 68% recall before translating too): all-13-language answer eval ≈96–99% per language; the remaining tail is one ranking issue (buergergeld-regelsatz in zh/ko) plus scattered per-language retrieval misses (steuerid-wo, kinderzuschlag-hoehe, arbeitsuchend-frist — also missed in German, so ranking, not language). 2026-07-21: `kinderzuschlag-hoehe` turned out to be a golden.jsonl labeling bug, not a retrieval miss — its chunk is crawled under topic `kindergeld`, not the `familie-und-kinder` the golden item claimed, so `chunk_is_relevant()`'s exact-topic check always failed it; fixed in golden.jsonl, retrieval recall@5 (de/en/zh-Hant) moved 89/100/89% → 95/100/95%. `steuerid-wo` (de) and `arbeitsuchend-frist` also turned out to already pass/fail independent of that bug on the current corpus — treat this whole line's misses list as stale until re-verified; a hybrid FTS5-keyword+vector retrieval fusion was tried to fix the remaining misses and reverted (net-hurt recall — see memory). Answer facts must tolerate locale number formats (space/NBSP thousands separators, Eastern Arabic digits) — Slavic locales write "1 800 €" and the eval falsely failed before those variants were added.

All offline — OpenAI, FAISS files and the PVOG API are stubbed (httpx.MockTransport / fake OpenAI client / temp DATA_DIR). **backend/tests/conftest.py must SET every path env var, never just pop** — `main.py` load_dotenv()s the developer's `.env`, and a popped `DATABASE_URL` comes back pointing at the real `data/metadata.db`, which fixtures then `drop_all()` (this happened; metadata.db is rebuildable from `merged.jsonl` without re-embedding because chunking is deterministic). `npm run build` doubles as the frontend typecheck.

**Production smoke test** (`scripts/smoke_test.py`, stdlib-only, run every 6 h by `.github/workflows/smoke-test.yml`; `python scripts/smoke_test.py [--base-url …]` locally): asks the *deployed* backend two real questions (de + zh-Hant) and asserts a substantial answer, non-empty sources, the router topic, and that the CORS header echoes the frontend origin. It exists because `/health` cannot see an unhealthy backend — on 2026-09-09 every /chat call 500'd for hours (OpenAI deprecated the default `CHAT_MODEL`, `gpt-5.3-chat-latest`, and the whole `*-chat-latest` line with it) while `/health` kept reporting `ok / index loaded`. Only a call that reaches the LLM catches that class of failure, so this one costs real OpenAI calls (with `RERANK=1`, one rerank + one answer completion per query) — keep the query list short. It retries once after 30 s so a deploy restart doesn't page anyone.

## Architecture notes

- **Vector DB is FAISS** (`IndexIDMap(IndexFlatIP)` over L2-normalized vectors = cosine). Index *building* (crawler's job) and index *loading* (backend's job, read-only at startup) stay separate — FAISS has no multi-process story, and under Railway each worker/replica loads the index independently.
- **Metadata DB**: SQLite (`sqlite:///data/metadata.db`) for local dev; production target is Railway PostgreSQL. Everything goes through SQLAlchemy, so switching is a `DATABASE_URL` change only. Metadata only (URLs, chunk text, topics, timestamps) — no vectors.
- **Paths**: always resolve relative to the repo root / `__file__`, never cwd. Relative sqlite/FAISS/output paths in env vars are anchored to the repo root by the code. (cwd-relative output paths silently wrote to `crawler/crawler/output/` twice before this convention.)
- **Deployment: Railway, two Docker services.** Each service's Root Directory (dashboard setting) is `backend` / `frontend`; each directory has its own `Dockerfile` + `railway.toml` (Railway config-as-code is per-service — one root file for both is not supported). The `data/` artifacts live on a **Railway volume mounted at `/data`** on the backend (`DATA_DIR` env, default `/data` in the image, `data` locally; relative values repo-root-anchored). The volume is populated by uploading locally built artifacts via `scripts/upload-index.sh` (wraps `railway volume files upload`; needs `railway login` + `railway link` once). **Uploading an *updated* index requires a redeploy** (`railway redeploy`): `RAGPipeline.load()` caches the FAISS index in memory for the process's lifetime (`rag.py:204` returns early once `self.index` is set), while `metadata.db` is read from disk per query through SQLAlchemy — so an upload without a restart leaves old in-memory vectors resolving IDs against a rebuilt `chunks` table and citing the wrong sources. Only the *first* population needs no restart (nothing is cached yet; `/health` flips degraded→ok on its own). `/health` cannot detect the stale case — it reports `index: loaded` either way. Frontend is a Next.js `standalone` build; `NEXT_PUBLIC_API_URL` is a **build-time** arg and must be the backend's **public** domain (the browser calls it — `.railway.internal` is unreachable from clients). Backend CORS: set `FRONTEND_ORIGIN` to the deployed frontend origin.
- Env vars live in `backend/.env` (`DATABASE_URL`, `DATA_DIR`, optional `FAISS_INDEX_PATH` override, `OPENAI_API_KEY`, production `FRONTEND_ORIGIN`); `crawler/build_index.py` also reads `backend/.env`.
- **Behörden-Finder is a live API integration, not crawled data**: responsibility depends on the user's location (~11k Kommunen), so `backend/behoerde.py` queries the official PVOG Suchdienst (`https://pvog.fitko.net/suchdienst/api`, public, no key) per request. Nothing PVOG goes into the FAISS index.
- **Bürgergeld → Grundsicherungsgeld rename** (effective 2026-07-01): official sites are mid-transition, both terms must stay in crawl keywords and be understood at query time (also in `behoerde.py`'s `TOPIC_QUERIES`, which tries both names against PVOG).

## Memory & note-taking

When generating summaries, architecture explanations, or project notes: automatically save the content as a Markdown file inside `./notes/` (e.g. `./notes/YYYY-MM-DD-topic.md`), creating the folder if it doesn't exist. Never save these to `/tmp` or another temp directory. Format the Markdown clearly with headers and code blocks.
