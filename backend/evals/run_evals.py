"""Golden-question evals against the real pipeline (index + OpenAI API).

Two modes:
  retrieval (default, embedding cost only, ~$0.001):
      For every question × language: embed, search top-5, count a hit when
      a retrieved chunk has the item's topic AND contains all its markers.
      Reports recall@5 per language — the cross-lingual gap is the number
      to watch (chunks are German, questions often aren't).
  --answers (adds one chat completion per question × language):
      Full pipeline answers, checked for: expected facts present, an
      expected source domain cited, no forbidden-script leaks, and the
      answer written in the requested language's script.

Usage (index + OPENAI_API_KEY required, backend/.env is loaded):
    python evals/run_evals.py                        # retrieval, all languages
    python evals/run_evals.py --languages de,zh-Hant
    python evals/run_evals.py --answers --limit 6    # answer eval subset
Run it before/after every prompt, model, chunking or crawl change.
"""

import argparse
import json
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

GOLDEN_PATH = Path(__file__).resolve().parent / "golden.jsonl"

CJK = re.compile(r"[一-鿿]")


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
    # Coarse language sanity: Chinese answers must contain Han characters,
    # German/English answers must not be dominated by them.
    has_cjk = bool(CJK.search(answer))
    language_ok = has_cjk if language.startswith("zh") else not has_cjk
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--languages", default="de,en,zh-Hant")
    parser.add_argument("--limit", type=int, default=None, help="first N golden items only")
    parser.add_argument("--answers", action="store_true", help="also run the full answer eval")
    args = parser.parse_args()

    from rag import RAGPipeline

    languages = args.languages.split(",")
    items = load_golden(args.limit)
    pipeline = RAGPipeline()

    retrieval_hits: dict[str, list[bool]] = {lang: [] for lang in languages}
    misses: list[str] = []
    for item in items:
        for lang in languages:
            question = item["questions"].get(lang)
            if not question:
                continue
            chunks = pipeline.retrieve(question)
            hit = any(chunk_is_relevant(c, item) for c in chunks)
            retrieval_hits[lang].append(hit)
            if not hit:
                misses.append(f"  MISS [{lang}] {item['id']}")

    print(f"Golden items: {len(items)} | languages: {', '.join(languages)}")
    print_summary("Retrieval recall@5 (relevant chunk in top-5):", retrieval_hits)
    if misses:
        print("\nRetrieval misses:")
        print("\n".join(misses))

    if not args.answers:
        return

    answer_pass: dict[str, list[bool]] = {lang: [] for lang in languages}
    failures: list[str] = []
    for item in items:
        for lang in languages:
            question = item["questions"].get(lang)
            if not question:
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


if __name__ == "__main__":
    main()
