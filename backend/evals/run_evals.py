"""Golden-question evals against the real pipeline (index + OpenAI API).

Two modes:
  retrieval (default, embedding cost only, ~$0.001):
      For every question × language: run pipeline.retrieve(), count a hit
      when a retrieved chunk has the item's topic AND contains all its
      markers. Reports recall@k per language, where k is however many
      chunks retrieve() returns (TOP_K=5 plain; up to TOP_K+RERANK_EXTRA_K
      with RERANK=1, so recall numbers are only comparable at equal k).
      The cross-lingual gap is the number to watch (chunks are German,
      questions often aren't).
  --answers (adds one chat completion per question × language):
      Full pipeline answers, checked for: expected facts present, an
      expected source domain cited, no forbidden-script leaks, and the
      answer written in the requested language's script.

Usage (index + OPENAI_API_KEY required, backend/.env is loaded):
    python evals/run_evals.py                              # print the cost estimate, call nothing
    python evals/run_evals.py --yes                        # retrieval, de/en/zh-Hant
    python evals/run_evals.py --yes --languages de,zh-Hant
    python evals/run_evals.py --yes --answers --limit 6    # answer eval subset
Run it before/after every prompt, model, chunking or crawl change.

Cost guard: without --yes the script only prints what the run would cost.
With --yes it tracks the actual cost of every OpenAI response and stops
before the next question once --max-usd (default $1) is reached. On
2026-09-10 unguarded eval runs (~$17-20) drained the prepaid OpenAI
balance that production shares, and /chat went down for everyone. Ask
before running paid evals (.claude/hooks/paid-api-guard.sh enforces that
for Claude Code).
"""

import argparse
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

GOLDEN_PATH = Path(__file__).resolve().parent / "golden.jsonl"

# Per-language script expectation: the answer must contain the language's
# own script; Latin-script languages must not contain any of the others
# (German terms stay Latin, so any Han/Hangul/Cyrillic/Arabic is a leak).
SCRIPTS = {
    "zh-Hant": re.compile(r"[一-鿿]"),
    "zh-Hans": re.compile(r"[一-鿿]"),
    "ko": re.compile(r"[가-힯]"),
    "ru": re.compile(r"[Ѐ-ӿ]"),
    "uk": re.compile(r"[Ѐ-ӿ]"),
    "ar": re.compile(r"[؀-ۿ]"),
    "fa": re.compile(r"[؀-ۿ]"),
}
NON_LATIN_ANY = re.compile(r"[一-鿿가-힯Ѐ-ӿ؀-ۿ぀-ヿ]")


def answer_language_ok(answer: str, language: str) -> bool:
    expected = SCRIPTS.get(language)
    if expected:
        return bool(expected.search(answer))
    return not NON_LATIN_ANY.search(answer)


def load_golden(limit: int | None) -> list[dict]:
    items = [json.loads(line) for line in GOLDEN_PATH.read_text().splitlines() if line.strip()]
    return items[:limit] if limit else items


def chunk_is_relevant(chunk, item: dict) -> bool:
    return chunk.topic == item["topic"] and all(m in chunk.content for m in item["markers"])


def check_answer(answer: str, sources: list[dict], item: dict, language: str) -> dict:
    from rag import FORBIDDEN_SCRIPTS

    facts_ok = all(any(alt in answer for alt in group) for group in item["facts"])
    source_ok = any(
        domain in (s.get("url") or "") for s in sources for domain in item["sources"]
    )
    script_ok = not FORBIDDEN_SCRIPTS.search(answer)
    language_ok = answer_language_ok(answer, language)
    return {
        "facts": facts_ok,
        "source": source_ok,
        "script": script_ok,
        "language": language_ok,
        "pass": facts_ok and source_ok and script_ok and language_ok,
    }


def print_summary(title: str, rows: dict[str, list[bool]]):
    print(f"\n{title}")
    for language, outcomes in rows.items():
        hits = sum(outcomes)
        pct = 100 * hits / len(outcomes) if outcomes else 0
        print(f"  {language:8s} {hits:2d}/{len(outcomes)}  ({pct:.0f}%)")


# Typical tokens per call, measured 2026-09-10 with reasoning effort "none"
# (rag.py). Default effort adds ~500 reasoning tokens to every chat call.
EST_TOKENS = {
    "translate": (80, 20),
    "embed": (30, 0),
    "rerank": (4500, 15),
    "answer": (2700, 500),
}


def estimate_usd(questions: int, translated: int, answers: bool) -> float:
    """Upper-bound-ish estimate for one run, from EST_TOKENS and budget.py prices."""
    import rag
    from budget import cost_usd

    def call(kind: str, model: str) -> float:
        prompt, completion = EST_TOKENS[kind]
        if kind in ("translate", "rerank", "answer"):
            effort = rag.ANSWER_REASONING_EFFORT if kind == "answer" else rag.HELPER_REASONING_EFFORT
            if effort != "none":
                completion += 500
        usage = SimpleNamespace(prompt_tokens=prompt, completion_tokens=completion)
        return cost_usd(model, usage)

    def one_retrieval(n: int, n_translated: int) -> float:
        per = call("embed", rag.EMBEDDING_MODEL) + (call("rerank", rag.RERANK_MODEL) if rag.RERANK else 0)
        return n * per + n_translated * call("translate", rag.CHAT_MODEL)

    total = one_retrieval(questions, translated)
    if answers:
        # query() retrieves again before answering.
        total += one_retrieval(questions, translated) + questions * call("answer", rag.CHAT_MODEL)
    return total


class SpendTracker:
    """on_usage callback: adds up what this run's OpenAI responses cost."""

    def __init__(self):
        self.usd = 0.0
        self.calls = 0

    def record(self, model, usage):
        from budget import cost_usd

        self.usd += cost_usd(model, usage)
        self.calls += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--languages",
        default="de,en,zh-Hant",
        help="comma list, or 'all' for every language in the golden set",
    )
    parser.add_argument("--limit", type=int, default=None, help="first N golden items only")
    parser.add_argument("--answers", action="store_true", help="also run the full answer eval")
    parser.add_argument("--yes", action="store_true", help="actually run (costs money); without it only the estimate is printed")
    parser.add_argument("--max-usd", type=float, default=1.0, help="stop before the next question once this much is spent (default 1.00)")
    args = parser.parse_args()

    import rag
    from rag import RAGPipeline

    items = load_golden(args.limit)
    if args.languages == "all":
        languages = list(items[0]["questions"])
    else:
        languages = args.languages.split(",")

    questions = sum(1 for item in items for lang in languages if item["questions"].get(lang))
    translated = sum(
        1 for item in items for lang in languages
        if item["questions"].get(lang) and (lang not in ("de", "en") or rag.NON_LATIN_QUERY.search(item["questions"][lang]))
    )
    estimate = estimate_usd(questions, translated, args.answers)
    print(
        f"Plan: {questions} questions ({len(items)} items x {len(languages)} languages)"
        f"{', with answers' if args.answers else ', retrieval only'}; RERANK={rag.RERANK}, "
        f"model {rag.CHAT_MODEL}, effort helper={rag.HELPER_REASONING_EFFORT!r} answer={rag.ANSWER_REASONING_EFFORT!r}"
    )
    print(f"Estimated cost: ~${estimate:.2f}  (stops at --max-usd ${args.max_usd:.2f})")
    if not args.yes:
        print("Nothing was sent. Re-run with --yes to spend it.")
        return
    if estimate > args.max_usd:
        print("Estimate exceeds --max-usd; the run will stop early unless you raise it.")

    spend = SpendTracker()
    pipeline = RAGPipeline(on_usage=spend.record)
    stopped_early = False

    def over_budget() -> bool:
        nonlocal stopped_early
        if spend.usd >= args.max_usd:
            stopped_early = True
        return stopped_early

    retrieval_hits: dict[str, list[bool]] = {lang: [] for lang in languages}
    misses: list[str] = []
    k_seen: set[int] = set()
    for item in items:
        for lang in languages:
            question = item["questions"].get(lang)
            if not question or over_budget():
                continue
            chunks = pipeline.retrieve(question, language=lang)
            k_seen.add(len(chunks))
            hit = any(chunk_is_relevant(c, item) for c in chunks)
            retrieval_hits[lang].append(hit)
            if not hit:
                misses.append(f"  MISS [{lang}] {item['id']}")

    print(f"Golden items: {len(items)} | languages: {', '.join(languages)}")
    k_label = str(max(k_seen)) if len(k_seen) == 1 else f"{min(k_seen)}-{max(k_seen)}"
    print_summary(f"Retrieval recall@k, k={k_label} (relevant chunk retrieved):", retrieval_hits)
    if misses:
        print("\nRetrieval misses:")
        print("\n".join(misses))

    if not args.answers:
        report_spend(spend, stopped_early, args.max_usd)
        return

    answer_pass: dict[str, list[bool]] = {lang: [] for lang in languages}
    failures: list[str] = []
    for item in items:
        for lang in languages:
            question = item["questions"].get(lang)
            if not question or over_budget():
                continue
            answer, sources = pipeline.query(question, language=lang, topic=item["topic"])
            result = check_answer(answer, sources, item, lang)
            answer_pass[lang].append(result["pass"])
            if not result["pass"]:
                failed = [k for k, v in result.items() if k != "pass" and not v]
                failures.append(f"  FAIL [{lang}] {item['id']}: {', '.join(failed)}")

    print_summary("Answer eval (facts + source + script + language):", answer_pass)
    if failures:
        print("\nAnswer failures:")
        print("\n".join(failures))
    report_spend(spend, stopped_early, args.max_usd)


def report_spend(spend: SpendTracker, stopped_early: bool, max_usd: float):
    print(f"\nActual cost: ${spend.usd:.3f} over {spend.calls} OpenAI calls")
    if stopped_early:
        print(f"STOPPED EARLY at the ${max_usd:.2f} cap — the numbers above cover only the questions run.")
        sys.exit(2)


if __name__ == "__main__":
    main()
