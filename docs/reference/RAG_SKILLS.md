# 🚀 Production-Ready RAG Chatbot Engineering Checklist

A checklist of engineering practices for production-grade RAG chatbots. Follow these constraints and best practices closely when designing, reviewing, or optimizing a RAG system.

The *"Lessons learned"* callout under each section is validated experience from this project (louvre-ar-backend, a full day of real development on 2026-07-20) — ready to reuse directly on future projects. Core ordering: **eval capability first (eval harness + judge validation) → retrieval quality calibration → production stability (dependency security, observability, distributed correctness).**

---

## 1. Ingestion & Preprocessing
- [ ] **Multi-modal & Structure Parsing**
  - For PDF, DOCX, or documents containing tables/images, don't use plain-text extraction; prefer a structured parser (e.g. Unstructured, MinerU, or LlamaParse) that preserves heading hierarchy and table Markdown structure.
- [ ] **Chunking Strategy**
  - Avoid fixed-size chunking; prefer **semantic chunking** or **recursive/Markdown header splitting**.
  - Set a chunk overlap (10%–20% recommended) to prevent context from being severed at cut points.
- [ ] **Deduplication**
  - Before writing embeddings to the vector database, deduplicate via hashing or semantic-similarity detection, to avoid redundant chunks wasting vector space and context window.

> **Lessons learned:** Chunking strategy should align with semantic units (e.g. section-level chunking), not just "smaller is better" — chunk boundaries should follow document structure. Index rebuilds should be a repeatable script/process, not a manual one-off operation.

---

## 2. Retrieval & Reranking
- [ ] **Hybrid Search**
  - Enable both **dense vector search** and **sparse BM25 search**.
  - Use **RRF (Reciprocal Rank Fusion)** or weighted fusion to balance semantic understanding against exact matching of proper nouns/model numbers.
- [ ] **Reranking Step**
  - After the vector DB's initial Top-K (e.g. Top-30), pass through a reranker (e.g. Cohere Reranker, ColBERT, or BGE-Reranker) to narrow down to the most relevant Top-N (e.g. Top-3–5).
- [ ] **Query Transformation**
  - For vague or short user questions, introduce query rewriting or HyDE (Hypothetical Document Embeddings) to improve retrieval recall.

> **Lessons learned:** Don't set the relevance threshold by feel — calibrate it against the live, real index with a script. At small corpus scale (~70 chunks, single source), a full BM25/RRF pipeline may be overkill — a cheap exact-match short-circuit for proper nouns (names, dates) can close most of the hybrid-search gap at a fraction of the infrastructure cost; revisit full hybrid search / reranking once the corpus or exhibit count scales up.

---

## 3. Context Window & Prompt Engineering
- [ ] **Dynamic Context Pruning**
  - Don't blindly stuff in raw retrieval results. Filter out irrelevant noise and keep only high-confidence passages, to avoid the "Lost in the Middle" effect in the LLM.
- [ ] **Prompt Caching Optimization**
  - Put the fixed, unchanging system prompt and core rules/constraints at the very front, and enable the LLM provider's caching mechanism (e.g. Anthropic Prompt Caching) to cut cost and latency.
- [ ] **Citations & Hallucination Guardrails**
  - The prompt must instruct the model to "answer strictly based on the provided context"; if the context has no relevant content, it must explicitly say "unable to answer / no information found."
  - Require the output to cite source indices (e.g. `[Source 1]`) so users can trace and verify.

> **Lessons learned:** The static prefix (persona + mode instructions) must come *before* any dynamic content (retrieved context, history notes) — a dynamic block anywhere before the tail invalidates the cached prefix for both OpenAI and Anthropic prefix caching. Structured `sources` metadata can be a better fit than inline `[Source N]` markers for non-text UIs (voice/AR).

---

## 4. State & Multi-Agent Coordination
- [ ] **Conversation Memory**
  - Separate short-term chat history from RAG knowledge-base retrieval; summarize/compact history periodically if it grows too long.
- [ ] **Routing & Fallback**
  - Introduce an intent classifier: small talk skips RAG; only technical/knowledge queries trigger the retrieval pipeline.
  - When RAG retrieval similarity falls below a confidence threshold, automatically hand off to a human agent or return a degraded-mode response.

> **Lessons learned:** A cheap whole-string regex short-circuit for pure chit-chat (greetings/thanks/bye) is enough to avoid burning a full retrieval + LLM call on "hi"/"thanks" — no need for a trained intent classifier at small scale. Match it against the *entire* stripped input, not a substring, so a real question that happens to start with "hi" still goes through RAG.

---

## 5. Observability & Evaluation
- [ ] **Tracing & Telemetry**
  - Integrate LangSmith, Arize Phoenix, or OpenTelemetry to fully record, per query: retrieval latency, embedding latency, reranker scores, token consumption, and model response time.
- [ ] **RAG Triad Evaluation**
  - Continuously measure three metrics via an automated evaluation framework such as Ragas or TruLens:
    1. **Context Relevance** (is the retrieved content relevant to the question?)
    2. **Groundedness / Faithfulness** (is the answer fully based on the retrieved content? any hallucination?)
    3. **Answer Relevance** (does the answer actually address the user's question?)

> **Lessons learned:**
> - Before adding features or fixing bugs, have an eval harness that can quantify "did this actually get better." Wire eval into CI as a required gate, not something run manually.
> - The LLM-as-judge itself needs validation: if the judge produces false negatives/positives (e.g. from under-sampled context relative to what the system actually retrieves), you'll misjudge whether the system got worse or better. **The judge's reliability needs verification just as much as the system under test.**
> - Build in structured logging from the start. Use response caching to cut cost/latency, but watch cache invalidation — a common RAG pitfall is documents updating while the cache stays stale. A hand-rolled eval harness tailored to your system's actual failure modes can outperform dropping in a generic framework (Ragas/TruLens) as-is.

---

## 6. Beyond the RAG Pipeline: Production Backend Practices

RAG-specific practices aren't sufficient on their own — these general backend practices matter just as much once the chatbot is in production:

- **CI/CD Architecture** — separate "fast and accurate checks" from "checks that automated PRs (e.g. Dependabot) can actually pass." Automated PRs usually can't trigger certain secrets/environments; required checks depending on those will block auto-updates indefinitely. Lint and unit tests must run in CI, not rely on human review alone.
- **Supply Chain & Dependency Security** — use a hash-pinned lockfile (e.g. pip-tools) for reproducibility and tamper resistance. Run pip-audit + Dependabot continuously for known CVEs. Regenerate the lockfile when changing language/runtime versions — wheel hashes can differ.
- **Distributed Correctness** — once there's more than one replica, rate limiting (and any other per-request counter) can't use in-process memory; use shared storage like Redis, or each replica counts independently and the limit becomes meaningless. This is the gap most often missed between "works on one machine" and "works in production with multiple replicas."
