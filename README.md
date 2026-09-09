# BürgerChat

[![ci](https://github.com/jeannineshiu/buergerchat/actions/workflows/ci.yml/badge.svg)](https://github.com/jeannineshiu/buergerchat/actions/workflows/ci.yml)

**German bureaucracy, explained in plain language — in 13 languages, always with official sources.**

BürgerChat is an AI assistant that helps people in Germany understand their rights and navigate public services. It translates Amtsdeutsch (official German) into simple language (einfache Sprache, B1 level), tells you **who is eligible, what to do, and which authority is responsible** — and finds the office in charge for your postal code, anywhere in Germany.

Built for the people official websites leave behind: migrants, refugees, and anyone who reads "Bedarfsgemeinschaft" and gives up.

## Why this exists

The gap between "having a right" and "getting it" in Germany is large, documented — and mostly a language and complexity problem:

- **25.2 million people in Germany — 30.4% — have a migration background** ([Mikrozensus 2024, Destatis](https://www.destatis.de/DE/Themen/Gesellschaft-Umwelt/Bevoelkerung/Migration-Integration/_inhalt.html)). 12.2 million hold no German passport, and about 63% immigrated themselves — many deal with German bureaucracy in a second language.
- **Official language fails almost everyone**: in a representative 2024 survey, only **4%** said they find Behördensprache understandable, over three quarters feel overwhelmed by it, and **one in four has already suffered a financial disadvantage** because of official letters or forms they couldn't understand ([Taxfix/Appinio survey, May 2024, n>2,000](https://taxfix.de/pm-behoerdensprache/)).
- **6.2 million German-speaking adults (12.1% of ages 18–64) read and write at low literacy levels** ([LEO 2018, Universität Hamburg](https://leo.blogs.uni-hamburg.de/leo-2018-62-millionen-gering-literalisierte-erwachsene/)). Einfache Sprache is not a nice-to-have; for them it is the access requirement.
- **Billions in benefits go unclaimed** ("verdeckte Armut"). Research puts non-take-up at roughly **60% for Grundsicherung im Alter** ([DIW 2019](https://www.diw.de/de/diw_01.c.699957.de/publikationen/wochenberichte/2019_49_1/starke_nichtinanspruchnahme_von_grundsicherung_deutet_auf_hohe_verdeckte_altersarmut.html)), **64–88% for Kinderzuschlag** and **~50–80% for Wohngeld**, and over a third for Bürgergeld ([BMAS research report 668](https://www.bmas.de/DE/Service/Publikationen/Forschungsberichte/fb-668-bestandsaufnahme-nichtinanspruchnahme-sozialleistungen.html)). The documented causes — not knowing the benefit exists, not understanding the process, stigma — are exactly what a plain-language assistant with an authority finder attacks.
- **Counseling doesn't scale to the demand**: the federally funded migration counseling service (MBE) reached **542,982 people in 2024**, up from 205,000 in 2012, across ~900 offices ([migrationsberatung.org](https://www.migrationsberatung.org/de/ueber-die-mbe)) — while its umbrella organisations report [chronic underfunding](https://www.bagfw.de/veroeffentlichungen/stellungnahmen/positionen/detail/migrationsberatung-fuer-erwachsene-zuwanderer-finanzielle-ausstattung-reicht-noch-immer-nicht-aus). A 24/7 assistant doesn't replace counselors, but it answers the recurring questions and points to the right office — the two things the MBE demand reports show people need most.

BürgerChat's topic priorities (benefits, family, housing, residence) follow that documented demand.

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

~6,100 documents (≈36,000 searchable passages) from official government sources only:

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
└──────────┘                 │  2. FAISS retrieval + rerank (36k)      │
                             │  3. live PVOG authority lookup (by PLZ) │
     ▲                       │  4. answer via LLM, grounded + cited    │
     │ sources, feedback     └─────────────────────────────────────────┘
     ▼                                        ▲
┌──────────┐    build_index   ┌───────────────┐
│ feedback │                  │ crawlers      │  sitemap/BFS, robots-
│ (SQLite) │                  │ (7 portals +  │  compliant, incremental
└──────────┘                  │  laws + BA)   │
                              └───────────────┘
```

- **Frontend**: Next.js (App Router, Tailwind), markdown-rendered answers, RTL support, per-message 👍/👎 and per-session star feedback
- **Backend**: FastAPI + FAISS (cosine over `text-embedding-3-small`) + OpenAI chat model (`gpt-5.5`, override via `CHAT_MODEL`)
- **Reranking** (`RERANK=1`, on in production): the vector search widens to 30 candidates and an LLM appends up to 3 extra picks *after* the untouched top-5. Union, not swap — swapping was zero-sum, the union took golden retrieval recall to 100% in all three eval languages, at one extra chat call per query
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
python portal_crawler.py           # ~2-2.5 h (robots crawl-delays)
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

- Land/city-level content beyond Berlin (muenchen.de …)
- Postgres for metadata/feedback (SQLite today; SQLAlchemy throughout, so it's a `DATABASE_URL` change)
- Deeper tax coverage (income tax rules — ELSTER portal docs are already in)

## Quality & engineering practices

**Correctness**

- **Golden-question evals** (`backend/evals/`): 19 questions with corpus-verified expected facts, each phrased in all 13 answer languages. `python evals/run_evals.py` measures retrieval recall@5 for de/en/zh-Hant (embedding cost only; `--languages all` covers the other ten); `--answers` adds full answer checks (facts, cited source, answer language). Run before/after every prompt, model, chunking or crawl change.
- **Offline test suites**: 96 backend + 41 crawler + 21 frontend tests run without network or API keys (OpenAI, FAISS and PVOG are stubbed).
- **CI on every push/PR** (`.github/workflows/ci.yml`): lint (ruff / eslint) + tests + `npm run build` (doubles as a typecheck) for all three modules, independently. Nothing merges on faith — the checks are the same ones described above, just automatic.
- **Production smoke test every 6 hours** (`scripts/smoke_test.py`, triggered by `.github/workflows/smoke-test.yml`): asks the deployed backend two real questions and checks the answer, the sources, the routed topic and the CORS header. `/health` only knows whether the index loaded — when OpenAI deprecated the answer model, every `/chat` call returned 500 while `/health` still reported `ok`. A monitor that never reaches the LLM would not have noticed.
- **Weekly re-crawl in Daytona sandboxes** (`scripts/daytona_recrawl.py`, triggered Sundays by `.github/workflows/weekly-crawl.yml`): an ephemeral [Daytona](https://www.daytona.io) sandbox crawls incrementally (state persists in a Daytona volume), rebuilds the index and stores it in the volume; `--download` pulls the latest index locally. Benefit amounts change every January — the eval baseline already caught the corpus drifting (Kindergeld 255 € in the 2025 crawl vs 259 € in 2026).

**Cost & reliability**

- **Chit-chat and meta-question short-circuits** (`backend/router.py`): pure small talk ("hi", "danke", "bye" — no actual question, matched in all 13 languages) and capability questions ("what can you do?") skip retrieval entirely instead of burning an embedding call + top-5 FAISS search on a message that was never going to use them.
- **Ingestion-time deduplication** (`crawler/build_index.py`): syndicated pages (arbeitsagentur.de republishes the same article per Ort) produce byte-identical chunks; these are dropped by content hash before embedding, not just at display time.
- **Rate limiting with a documented scaling gap**: per-IP limits via slowapi default to in-process memory, which is correct for today's single Railway replica but would silently multiply every limit if a second replica were added. An opt-in `RATELIMIT_STORAGE_URI` (Redis) makes shared counting a config change, not a code change — main.py warns at startup if it looks like production without it set.

**Dependency hygiene**

- **`pip-audit` gate in CI** for both Python modules, plus **Dependabot** (pip ×2, npm, github-actions) opening weekly update PRs — so known-CVE dependencies fail the build instead of going unnoticed, and version drift shows up as a reviewable PR instead of staying stale indefinitely.
- Backend and crawler are independent modules (see [For contributors](#for-contributors)) but share **one local conda env** — cross-module pins that drift apart (e.g. two different `faiss-cpu` versions) break local dev even though each module's isolated CI job stays green, so shared-dependency bumps (faiss-cpu, numpy, pytest) are kept in lockstep across both `requirements.txt` files.

## For contributors

Module-level conventions, schemas and operational details live in [CLAUDE.md](CLAUDE.md). The three modules (frontend / backend / crawler) are deliberately decoupled — crawler and backend share data schemas, never code.

## License

[MIT](LICENSE)
