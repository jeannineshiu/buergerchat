# BürgerChat

**German bureaucracy, explained in plain language — in 13 languages, always with official sources.**

BürgerChat is an AI assistant that helps people in Germany understand their rights and navigate public services. It translates Amtsdeutsch (official German) into simple language (einfache Sprache, B1 level), tells you **who is eligible, what to do, and which authority is responsible** — and finds the office in charge for your postal code, anywhere in Germany.

Built for the people official websites leave behind: migrants, refugees, and anyone who reads "Bedarfsgemeinschaft" and gives up.

## What it can do

💬 **Answer questions about**

| Topic | Examples |
|---|---|
| Bürgergeld / Grundsicherungsgeld | Am I eligible? How much? What are my obligations? |
| Kindergeld & family benefits | Kindergeld, Kinderzuschlag, Elterngeld, Unterhaltsvorschuss |
| Unemployment | Arbeitslosengeld, Jobcenter procedures |
| Pension (Rente) | Retirement ages, Erwerbsminderung, survivor pensions |
| Wohngeld | Housing allowance eligibility and application |
| Taxes | Steuer-ID and other BZSt matters |
| Residence & citizenship | Visas, Aufenthaltstitel, Einbürgerung, integration courses |

🏛️ **Find your responsible authority** — nationwide, down to the municipal level. Give it your postal code and it names the concrete office (your Jobcenter, Wohngeldstelle, Bürgeramt …) with address, phone and website, live from the official [PVOG](https://docs.fitko.de/resources/pvog/) federal registry — for *any* public service, not just the topics above.

🌍 **Answer in your language** — Deutsch, English, Türkçe, العربية, فارسی, Українська, Русский, Polski, 繁體中文, 简体中文, Tiếng Việt, Bahasa Indonesia, 한국어. Official German terms stay in German (you'll need them at the Amt) with a short explanation in your language.

📎 **Always cite official sources** — every answer links the government pages and laws it is based on. Answers are grounded strictly in retrieved official content; when the knowledge base doesn't cover something, it says so instead of guessing.

## What it knows

~4,800 documents (≈28,000 searchable passages) from official federal sources only:

- **arbeitsagentur.de** — Bürgergeld, Kindergeld, unemployment
- **familienportal.de** — all family benefits (BMFSFJ)
- **deutsche-rentenversicherung.de** — pensions
- **bmwsb.bund.de** — Wohngeld
- **bzst.de** — Steuer-ID, taxes
- **bamf.de** — residence, asylum, integration
- **gesetze-im-internet.de** — 9 laws, section by section: SGB I/II/VI/VIII/X/XII, BKGG, WoGG, AufenthG
- **service.berlin.de** — all Berlin public services (requirements, documents, fees, deadlines)
- **elster.de** — using the official online tax portal (registration, certificates, einfachELSTER)

Topic selection follows the documented demand of migration counseling services (MBE reports): unemployment benefits, housing, family benefits and residence status are what people actually need help with.

**Scope**: federal rules (valid Germany-wide) plus Berlin as the first city with local service details. Other Länder/city specifics are not (yet) covered; the authority finder, however, covers all ~11,000 municipalities.

> ⚠️ BürgerChat explains official information. It is not legal advice, and it tells users so.

## How it works

```
┌──────────┐   POST /chat    ┌─────────────────────────────────────────┐
│ Next.js  │ ──────────────► │ FastAPI backend                         │
│ chat UI  │                 │  1. topic + intent routing (rule-based) │
└──────────┘                 │  2. FAISS retrieval (27k chunks)        │
                             │  3. live PVOG authority lookup (by PLZ) │
     ▲                       │  4. answer via LLM, grounded + cited    │
     │ sources, feedback     └─────────────────────────────────────────┘
     ▼                                        ▲
┌──────────┐    build_index   ┌───────────────┐
│ feedback │                  │ crawlers      │  sitemap/BFS, robots-
│ (SQLite) │                  │ (5 portals +  │  compliant, incremental
└──────────┘                  │  laws + BA)   │
                              └───────────────┘
```

- **Frontend**: Next.js (App Router, Tailwind), markdown-rendered answers, RTL support, per-message 👍/👎 and per-session star feedback
- **Backend**: FastAPI + FAISS (cosine over `text-embedding-3-small`) + OpenAI chat model (`gpt-5.4-mini`, override via `CHAT_MODEL`)
- **Authority finder**: live queries against the public PVOG Suchdienst API (PLZ → ARS → service → responsible organisation unit)
- **Crawlers**: sitemap-driven (or restricted BFS), honor robots.txt including per-site crawl delays, re-runnable incrementally
- **Deployment**: two Docker services on Railway; index artifacts live on a volume (`/data`), uploaded via `scripts/upload-index.sh`

## Getting started (local)

Prerequisites: conda (Python 3.11), Node 20+, an OpenAI API key.

```bash
# 1. Environment
conda create -n buergerchat python=3.11 -y
conda activate buergerchat
pip install -r backend/requirements.txt -r crawler/requirements.txt

# 2. Build the knowledge base (or copy an existing data/ directory)
cd crawler
python arbeitsagentur_crawler.py   # ~45 min
python gesetze_crawler.py          # seconds
python portal_crawler.py           # ~1.5-2 h (robots crawl-delays)
python build_index.py              # chunk + embed + write data/

# 3. Backend
cd ../backend
cp .env.example .env               # add OPENAI_API_KEY
uvicorn main:app --reload          # http://localhost:8000

# 4. Frontend
cd ../frontend
npm install
npm run dev                        # http://localhost:3000
```

## API

| Endpoint | Description |
|---|---|
| `POST /chat` | `{message, language, history[]}` → `{answer, sources[], topic}`; 503 while the index is missing |
| `GET /health` | `{status: ok\|degraded, index: loaded\|missing}` — always 200 |
| `POST /feedback/message` | 👍/👎 + optional comment per answer |
| `POST /feedback/session` | 1–5 stars per conversation |

## Roadmap

- Land/city-level content (service.berlin.de, muenchen.de …)
- Weekly re-crawl automation
- Postgres for metadata/feedback (SQLite today; SQLAlchemy throughout, so it's a `DATABASE_URL` change)
- Deeper tax coverage (income tax rules — ELSTER portal docs are already in)

## For contributors

Module-level conventions, schemas and operational details live in [CLAUDE.md](CLAUDE.md). The three modules (frontend / backend / crawler) are deliberately decoupled — crawler and backend share data schemas, never code.
