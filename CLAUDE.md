# CLAUDE.md

buergerchat is a RAG chatbot for German government services (全德國政府服務 RAG chatbot): it translates official German documents into plain language (einfache Sprache), always citing original sources, and answers must be actionable (eligibility, steps, responsible Behörde). MVP themes in priority order: Bürgergeld / Neue Grundsicherung, Kindergeld, finding the right Behörde; the knowledge base also covers Rente, Wohngeld, Steuern, Aufenthalt/Einbürgerung and family benefits. Domain vocabulary lives in `CONTEXT.md`. The reasons behind the rules below (incidents, measured numbers) are in `docs/claude-md-history.md`.

## Structure

```
frontend/   Next.js (App Router) chat UI; /api proxies to the backend
backend/    FastAPI (Python 3.11) RAG chat API
crawler/    crawlers + index build
data/       built FAISS index + SQLite metadata DB (gitignored, regenerable)
scripts/    recrawl, ship/download index, production smoke test
```

Crawler and backend never import from each other; they agree on schemas instead — JSONL records `{url, title, content, topic, crawled_at}` (+ `law` for gesetze) and the `chunks` table (`chunks.id` doubles as the FAISS vector ID).

## Environment

One shared **conda** env for backend and crawler (the user chose conda; no python3.11 outside it):

```bash
conda activate buergerchat
pip install -r backend/requirements.txt -r crawler/requirements.txt
```

backend and crawler pin the same `faiss-cpu`/`numpy` versions; move them together or the combined install conflicts.

Run: `cd backend && uvicorn main:app --reload` (needs `backend/.env`, see `.env.example`); `cd frontend && npm run dev` (its `/api` proxy expects the backend on :8000, `BACKEND_URL` to override). The app boots without an index — `/health` reports `degraded` and `/chat` answers 503 until `data/` is built.

Tests (offline — OpenAI, FAISS files and PVOG are stubbed):

```bash
cd backend && python -m pytest tests/     # needs requirements-dev.txt
cd crawler && python -m pytest tests/
cd frontend && npm test                   # npm run build doubles as the typecheck
```

## Paid calls — ask first

The local OpenAI key is production's key and project: a local run that hits the spend limit takes /chat down for everyone.

- Before any command that calls OpenAI, quote the cost estimate and get the user's OK. `python evals/run_evals.py` without `--yes` prints the plan and estimate; `--yes` runs it, capped by `--max-usd` (default $1). `.claude/hooks/paid-api-guard.sh` forces a prompt for `run_evals.py … --yes` and `smoke_test.py --mode full`; ad-hoc scripts that import `rag.py` are on you.
- `backend/budget.py` costs every OpenAI response into `usage.db`; once today's UTC total reaches `DAILY_BUDGET_USD` /chat answers 503 `daily_budget_exhausted`. **Update its price table whenever a model or price changes.**
- Golden set `backend/evals/golden.jsonl`: an item's topic and all its markers must sit in one chunk of metadata.db; facts must be language-neutral (digits, German proper nouns) and tolerate locale number formats.

## Backend rules

- `/chat` is thin: `turn_plan.TurnPlanner.plan()` → `RAGPipeline.answer(plan)`. Routing decisions (turn kind, topic, authority outcome, PLZ, history fallbacks) belong in `turn_plan.py`; prompt directives in `rag.py`; what becomes a Source (context numbering, the QUELLEN line, dedupe, the Behörde's source) in `sources.py`. Evals build `TurnPlan.direct(...)`.
- Router keywords cover German phrasing only, so every non-German message is routed on its German translation (`RAGPipeline.to_german`). Retrieval embeds the translation too, except English, which embeds untranslated.
- `RERANK=1` is set in production (off in code): vector top-5 stays untouched and the LLM rerank *appends* up to `RERANK_EXTRA_K` picks — union, never swap.
- Reasoning effort is explicit per call (`HELPER_REASONING_EFFORT`, `ANSWER_REASONING_EFFORT`, default `none`); `""` omits the parameter for non-reasoning models. Model history is in the comment in `rag.py`.
- Answers write figures as digits (ar/fa may keep their own); a regex guard retries once when an answer leaks a script no answer language uses.
- `feedback.db` and `usage.db` are separate sqlite files in `DATA_DIR`, never tables in `metadata.db` — the index ship replaces metadata.db wholesale.
- Rate-limit counts live in process memory. Set `RATELIMIT_STORAGE_URI` (redis) before running more than one replica, or every limit silently multiplies.
- The first-turn answer cache is in memory and cleared by a redeploy (the index ship relies on that); `Cache-Control: no-cache` skips it.
- **Behörden-Finder** (`behoerde.py`) queries the live PVOG Suchdienst per request; nothing PVOG goes into the index. PVOG never answers "no match" — it returns its nearest rows — so every hit must pass `is_relevant()` against the query's key word before it is offered. Any failure returns `None` and /chat degrades gracefully.
- **Bürgergeld → Grundsicherungsgeld** (renamed 2026-07-01): official sites are mid-transition, so both names stay in crawl keywords, router keywords and `TOPIC_QUERIES`.
- `backend/tests/conftest.py` must **set** every path env var, never pop one: `main.py` load_dotenv()s the developer's `.env`, and a popped `DATABASE_URL` points fixtures at the real `data/metadata.db`.

## Crawler rules

- Crawlers send User-Agent `BuergerChat-Bot/1.0 (educational project)`, sleep 1–2 s between requests and honour robots Crawl-delay (bzst 30 s, DRV 12 s). They are incremental: re-running skips crawled URLs and appends.
- gesetze-im-internet.de pages are ISO-8859-1. `portal_crawler.py` uses the lxml parser (service.berlin.de breaks html.parser).
- `build_index.py` reuses vectors of byte-identical chunks and writes nothing when the chunk list is unchanged. After changing `EMBEDDING_MODEL` run it with `--full` — the build doesn't record which model made its vectors.

## Paths

Resolve every path relative to the repo root / `__file__`, never cwd; relative sqlite/FAISS/output paths in env vars are anchored to the repo root by the code.

## Deployment

- Railway, project `lively-recreation`: backend service `buergerchat` (volume `buergerchat-volume` at `/data`), frontend service `profound-balance`; live at `https://buergerchat-production.up.railway.app`. Each service has its own `Dockerfile` + `railway.toml` in its directory. Metadata DB is still SQLite in production (Postgres not done; SQLAlchemy makes it a `DATABASE_URL` change).
- **Pushing to `main` deploys both services.** Treat every push as a production release.
- **An index upload needs a redeploy**: `RAGPipeline.load()` caches the FAISS index for the process lifetime while metadata.db is read per query, so without a restart old vectors resolve against new chunks and cite wrong sources — and `/health` can't see it. `scripts/ship-index.sh` uploads as `*.new`, renames keeping `*.prev`, redeploys and waits; roll back with `RESTORE=prev scripts/ship-index.sh`.
- The browser only talks to the frontend's same-origin `/api` proxy (`src/lib/proxy.ts`), which forwards to `BACKEND_URL` over Railway's private network. The proxy must forward `X-Forwarded-For` — the backend rate-limits on its first hop.
- **Weekly re-crawl** runs on the GitHub runner (`.github/workflows/weekly-crawl.yml` → `scripts/recrawl.sh`; secrets `OPENAI_API_KEY`, `RAILWAY_TOKEN`, `RAILWAY_SSH_KEY`, whose public half must be registered with `railway ssh keys add`). Crawl state carries over as the `crawl-state` artifact of the last successful run; the index is published as the `index` artifact (public repo → public artifact). If the build changed, the run ships and runs the full smoke test. A run that built but failed to ship: `gh workflow run ship-index.yml -f run_id=<id>` (its own workflow, so it never becomes the run that carries crawl state). `scripts/download-index.sh` pulls an `index` artifact into `data/`.
- **Smoke test** (`scripts/smoke_test.py`): `--mode free` (daily) checks `/health` + `/health/model` — OpenAI doesn't bill the models endpoint, and it catches a deprecated model or dead key that `/health` can't. `--mode full` (Mondays + after every ship, ~$0.10) asks two real questions through the frontend proxy. Keep its query list short.

## Notes

When writing summaries, architecture explanations or project notes, save them as Markdown in `./notes/YYYY-MM-DD-topic.md` (never `/tmp`).

## Agent skills

- Issues: GitHub Issues (jeannineshiu/buergerchat) via `gh` — see `docs/agents/issue-tracker.md`; labels in `docs/agents/triage-labels.md`.
- Domain docs: root `CONTEXT.md` + `docs/adr/` (created lazily) — see `docs/agents/domain.md`.
