#!/usr/bin/env python3
"""Smoke-test the deployed app by asking it real questions.

Motivated by the 2026-09-09 outage: OpenAI deprecated the model that was
`CHAT_MODEL`'s default, so every /chat call 500'd for hours while nothing
in the project had changed. `/health` could not see it — it only reports
whether the FAISS index is loaded, and it was. Only an end-to-end call
that actually reaches the LLM catches that class of failure, so this
script makes one (per language) and checks the response is a real answer.

It goes through the frontend's same-origin /api proxy — the exact path a
browser takes — so a broken proxy or a wrong BACKEND_URL on the frontend
service fails it too. Pointing --base-url at the backend itself also works
(same /health and /chat paths).

Stdlib only, no dependencies: it runs from a bare GitHub Actions runner
(see .github/workflows/smoke-test.yml) and from any local shell.

    python scripts/smoke_test.py
    python scripts/smoke_test.py --base-url http://localhost:3000/api
    python scripts/smoke_test.py --base-url http://localhost:8000   # backend only

Exit code 0 = healthy, 1 = something is broken (details on stderr).
Each run costs a couple of OpenAI calls per query — with RERANK=1 that is
one rerank plus one answer completion — so keep the query list short and
the cron interval sane.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://buergerchat.up.railway.app/api"

# One query per language family we care about, with the topic the
# rule-based router must assign. Topics are deterministic (router.py is
# keyword-based), so asserting them is a real check and not a flake; the
# answer text itself is only checked for being substantial, since wording
# varies per run.
QUERIES = [
    {"message": "Was ist Bürgergeld?", "language": "de", "topic": "buergergeld"},
    {"message": "我可以領 Kindergeld 嗎？", "language": "zh-Hant", "topic": "kindergeld"},
]

# Long enough to rule out an empty or one-line degenerate answer, short
# enough that a legitimately brief answer never trips it.
MIN_ANSWER_CHARS = 80
# /chat does retrieval, an optional rerank call and an answer completion.
CHAT_TIMEOUT = 120


class SmokeFailure(Exception):
    """A check failed; the message is what gets reported."""


def _request(url, *, payload=None, timeout=30):
    """Return (status, parsed_body). Raises SmokeFailure on transport errors."""
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode()
            status = response.status
    except urllib.error.HTTPError as exc:
        # An error response still carries a body — FastAPI's detail or the
        # 503 {"error": ...} the backend returns while the index is missing.
        # A 500 body is just "Internal Server Error"; the traceback that
        # names the actual cause is only in the service log.
        body = exc.read().decode(errors="replace")[:500]
        # 502/504 come from the frontend proxy (backend unreachable / timed
        # out); other 5xx from the backend itself.
        if exc.code in (502, 504):
            hint = " (proxy: check BACKEND_URL / `railway logs -s profound-balance`)"
        elif exc.code >= 500:
            hint = " (see `railway logs -s buergerchat`)"
        else:
            hint = ""
        raise SmokeFailure(f"HTTP {exc.code} from {url}: {body}{hint}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise SmokeFailure(f"could not reach {url}: {exc}") from exc

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        parsed = None
    return status, parsed


def check_health(base_url):
    _, body = _request(f"{base_url}/health")
    if not isinstance(body, dict):
        raise SmokeFailure("/health did not return JSON")
    # /health is 200 even when broken: `degraded` means the volume has no
    # index yet, which /chat answers with a 503.
    if body.get("status") != "ok" or body.get("index") != "loaded":
        raise SmokeFailure(f"/health reports {body}")
    return "/health: ok, index loaded"


def check_chat(base_url, query):
    _, body = _request(
        f"{base_url}/chat",
        payload={"message": query["message"], "language": query["language"], "history": []},
        timeout=CHAT_TIMEOUT,
    )
    if not isinstance(body, dict):
        raise SmokeFailure(f"/chat [{query['language']}] did not return JSON")

    label = f"/chat [{query['language']}]"
    answer = (body.get("answer") or "").strip()
    if len(answer) < MIN_ANSWER_CHARS:
        raise SmokeFailure(f"{label} answer too short ({len(answer)} chars): {answer!r}")

    sources = body.get("sources") or []
    if not sources:
        raise SmokeFailure(f"{label} returned no sources — retrieval found nothing")
    if any(not s.get("url") for s in sources):
        raise SmokeFailure(f"{label} returned a source without a url: {sources}")

    topic = body.get("topic")
    if topic != query["topic"]:
        raise SmokeFailure(f"{label} routed to topic {topic!r}, expected {query['topic']!r}")

    return f"{label}: {len(answer)} chars, {len(sources)} sources, topic {topic}"


def run_checks(base_url):
    """Run every check, collecting failures instead of stopping at the first."""
    passed, failed = [], []
    for name, check in [
        ("health", lambda: check_health(base_url)),
        *[
            (f"chat-{q['language']}", (lambda q=q: check_chat(base_url, q)))
            for q in QUERIES
        ],
    ]:
        try:
            passed.append(check())
        except SmokeFailure as exc:
            failed.append(f"{name}: {exc}")
    return passed, failed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.environ.get("SMOKE_BASE_URL", DEFAULT_BASE_URL),
        help="API base URL: the frontend's /api proxy or the backend (env: SMOKE_BASE_URL)",
    )
    parser.add_argument(
        "--retry-delay",
        type=int,
        default=30,
        help="seconds to wait before the single retry (0 disables the retry)",
    )
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    print(f"Smoke-testing {base_url}", flush=True)
    passed, failed = run_checks(base_url)

    # A deploy restart or a blip should not page anyone; a real breakage
    # survives one retry.
    if failed and args.retry_delay:
        print(f"{len(failed)} check(s) failed, retrying in {args.retry_delay}s…", flush=True)
        for failure in failed:
            print(f"  first attempt: {failure}", flush=True)
        time.sleep(args.retry_delay)
        passed, failed = run_checks(base_url)

    for line in passed:
        print(f"PASS  {line}")
    for line in failed:
        print(f"FAIL  {line}", file=sys.stderr)

    if failed:
        print(f"\n{len(failed)} check(s) failed", file=sys.stderr)
        return 1
    print(f"\nAll {len(passed)} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
