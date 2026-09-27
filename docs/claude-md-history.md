# CLAUDE.md history — the reasons behind its rules

On 2026-09-27 CLAUDE.md was pruned down to the rules an agent needs every
session. The incident stories, measured numbers and model history it used to
carry moved here, so each rule in CLAUDE.md still has its "why" one lookup away.
Files named `YYYY-MM-DD-*.md` below are the fuller write-ups in `notes/`, which
is gitignored (local only).
Dated entries are what was true then; re-verify before quoting a number.

## Paid calls and the budget

- **2026-09-10 — prepaid OpenAI balance ran dry.** ~$17–20 of golden evals ran
  without asking; local evals share the OpenAI key and project with
  production, so /chat 500'd for everyone. Led to: `backend/budget.py`
  (daily spend cap, `DAILY_BUDGET_USD`, default `0.50`), the
  `.claude/hooks/paid-api-guard.sh` hook, and the "ask before evals" rule.
  A separate dev project/key is still recommended. See
  `2026-09-10-openai-credits-and-spend-limits.md`.
- Eval costs (then): de/en/zh-Hant retrieval with `RERANK=1` ≈ $1.3 (every
  question also pays a gpt-5.5 rerank call, ~4.5k input tokens) vs ≈ $0.001 for
  embeddings alone; `--answers` over all 13 languages ≈ $19.
- The smoke test's full mode costs ~$0.10 of the daily budget per run. It ran
  daily until 2026-09-23 (~$3/month), then moved to weekly while the free
  model check took the daily slot.

## Models

- **2026-09-09 — default CHAT_MODEL deprecated.** OpenAI retired
  `gpt-5.3-chat-latest` and the whole `*-chat-latest` line; every /chat call
  404'd → 500 for hours while `/health` kept reporting `ok / index loaded`.
  Default moved to gpt-5.5. This is why the smoke test exists and why
  `/health/model` (unbilled `models.retrieve()`) runs daily. See
  `2026-09-09-chat-500-model-deprecated.md`.
- Earlier candidates: 4o-mini code-switched between languages; 5.4-mini
  ignored the no-offer style rules (full history in the comment in `rag.py`).
- **Reasoning effort `none` (2026-09-10):** at gpt-5.5's default effort the
  rerank spent ~512 reasoning tokens to emit a dozen digits. `none` took /chat
  from a 15–20 s median to 5–7.5 s with equal golden-eval quality.
- **Digits directive:** zh answers used to spell figures in Chinese numerals
  (五百六十三歐元, 4–5 of 19 zh-Hant answers), which the digit-only fact check
  failed. After the directive, the 2026-09-10 answer eval went 19/19 in
  de/en/zh-Hant/zh-Hans/ko/ar with 0 spelled-out figures.
- **Script-leak guard:** both 5.x models occasionally emit Thai ย้อนหลัง for
  "retroactive" in Chinese answers.

## Retrieval and evals

- **Rerank union (enabled in production 2026-08-09):** swap mode was
  zero-sum and net-hurt recall; union (vector top-5 untouched + ≤3 LLM picks)
  took golden retrieval recall de/en/zh-Hant to 100/100/100%.
- **Query translation:** embedding aligns only German and English well with
  the German corpus; tr/pl/vi/id sat at 68% recall before their queries were
  translated too. English is embedded untranslated (recall@5 en was 100% that
  way) but still translated for routing, so it costs one extra helper call.
- **Baseline 2026-07-18** (stale corpus, no query translation): retrieval de
  84% / en 95% / zh-Hant 63%; answers de 88% / en 88% / zh-Hant 62%; every
  answer failure tracked a retrieval miss.
- **2026-07-19** (re-crawl + query→German translation): all-13-language answer
  eval ≈96–99% per language.
- **2026-07-21:** `kinderzuschlag-hoehe` was a golden.jsonl labeling bug (its
  chunk is crawled under `kindergeld`, not `familie-und-kinder`), not a
  retrieval miss; fixing it moved recall@5 (de/en/zh-Hant) 89/100/89% →
  95/100/95%. A hybrid FTS5-keyword + vector fusion was tried for the remaining
  misses and reverted — it net-hurt recall. See
  `2026-07-21-golden-jsonl-topic-bug-and-notetaking-rule.md`.
- Slavic locales write "1 800 €"; the eval falsely failed before the
  space/NBSP-thousands and Eastern-Arabic-digit variants were added.

## Infrastructure

- **Daytona → GitHub runner (2026-09-20):** the weekly re-crawl ran in a
  Daytona sandbox until Daytona started rejecting per-sandbox
  `domainAllowList` on Tier 1/2, and the tier-default egress doesn't reach the
  government sites.
- **Railway SSH key:** `railway volume files` runs over SSH; without a
  registered key the CLI prints "No SSH keys found." and the ship fails. See
  `2026-09-27-weekly-crawl-ship-failure.md`.
- **2026-09-10 — Firefox request dropped.** The browser used to call the
  backend directly; `up.railway.app` is a public suffix, so that was a
  cross-site request with a CORS preflight, and a Firefox user's request was
  dropped before reaching Railway (extension or company web filter). Led to
  the same-origin `/api` proxy. See `2026-09-10-firefox-chat-request-blocked.md`.
- **conftest drop_all incident:** a popped `DATABASE_URL` came back from
  `.env` pointing at the real `data/metadata.db`, which fixtures then
  `drop_all()`'d. metadata.db is rebuildable from `merged.jsonl` without
  re-embedding because chunking is deterministic.
- **cwd-relative output paths** silently wrote to `crawler/crawler/output/`
  twice before the repo-root-anchoring convention.
- **faiss-cpu 1.8.0** segfaulted/ImportErrored under NumPy 2.x (hence the old
  numpy<2 pin); resolved as of faiss-cpu 1.14.3.
- **PVOG irrelevant hits:** before the relevance check, "Which office is
  responsible? 10115" was answered with the BaFin arbitration board in Bonn,
  address included. A Hamburg entry named "Informationen" used to beat the
  Familienkasse by being local.
