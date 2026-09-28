"""The Source list of one answer (see Source in CONTEXT.md).

A source is only a page the answer draws on, not everything retrieved —
with RERANK up to top-5 + RERANK_EXTRA_K chunks reach the context. The
context blocks are numbered [n]; the answer names the ones it used on a last
"QUELLEN: 1, 3" line, which is stripped before the answer is shown. The
numbering, the directive that asks for the line and the parser that reads it
live here together, so they can't drift apart.
"""

import re
import sys
from typing import Sequence

from behoerde import BehoerdeResult

# Also named in rag.SYSTEM_PROMPT, which tells the model to name this Behörde.
AUTHORITY_HEADER = "[Zuständige Stelle laut Behördenfinder (PVOG)]"

USED_SOURCES_LINE = re.compile(r"(?:^|\n)[ \t*]*QUELLEN[ \t*]*[:：]([^\n]*)\s*\Z", re.IGNORECASE)
NONE_USED = {"-", "–", "—", "keine", "none"}

DIRECTIVE = (
    "End with one last line exactly in the form 'QUELLEN: 1, 3' naming "
    "the numbers of the context blocks [n] your answer draws on; the "
    "Behördenfinder block has no number and is never listed. Write "
    "'QUELLEN: -' if you used none. Keep the word QUELLEN on that line "
    "in every answer language, and never put block numbers like [1] "
    "in the answer text itself."
)


def split_used_sources(answer: str) -> tuple[str, set[int] | None]:
    """Strip a trailing QUELLEN line; return the answer and the context block
    numbers it names — None when there is no usable line, so the caller keeps
    every retrieved page rather than dropping real sources."""
    match = USED_SOURCES_LINE.search(answer)
    if not match:
        return answer, None
    listed = match.group(1).strip(" \t*")
    # \d also matches Arabic/Persian digits, and int() reads them.
    numbers = {int(n) for n in re.findall(r"\d+", listed)}
    if numbers:
        used: set[int] | None = numbers
    elif listed.lower() in NONE_USED:
        used = set()
    else:
        used = None
    return answer[: match.start()].rstrip(), used


class SourceList:
    """chunks: the retrieved chunks in rank order (anything with url, title
    and content); authority: the Behörden-Finder's result, if it found one."""

    def __init__(self, chunks: Sequence, authority: BehoerdeResult | None = None):
        self._chunks = list(chunks)
        self._authority = authority

    def context_text(self) -> str:
        """The context the answer is written from: the Behörde first, then
        the chunks as numbered blocks."""
        text = "\n\n".join(f"[{i}] {c.title}\n{c.content}" for i, c in enumerate(self._chunks, 1))
        if self._authority is not None:
            text = f"{AUTHORITY_HEADER}\n{self._authority.context_block()}\n\n{text}"
        return text

    def directive(self) -> str | None:
        """The prompt directive asking for the QUELLEN line; None when there
        are no numbered blocks to name."""
        return DIRECTIVE if self._chunks else None

    def answer_text(self, reply: str) -> str:
        """The reply as the reader sees it, QUELLEN line stripped."""
        return split_used_sources(reply)[0] if self._chunks else reply

    def resolve(self, reply: str, retry_reply: str | None = None) -> tuple[str, list[dict]]:
        """(answer text, sources) for the model's reply. retry_reply: the
        rewrite a language retry produced, which is what the reader gets."""
        answer, used = split_used_sources(reply) if self._chunks else (reply, None)
        if retry_reply is not None:
            answer, retry_used = split_used_sources(retry_reply)
            # A rewrite for language often drops the QUELLEN line; the blocks
            # the first answer drew on are still the ones it used.
            if retry_used is not None:
                used = retry_used

        # Several of the top-K chunks often come from the same (long) page —
        # fine for the context, but the visible source list should name each
        # page once, in retrieval order. Titles dedupe too: arbeitsagentur.de
        # syndicates the same article under per-Ort URLs.
        sources = []
        seen_urls: set[str] = set()
        seen_titles: set[str] = set()
        for i, c in enumerate(self._chunks, 1):
            if used is not None and i not in used:
                continue
            # Normalized title: syndicated copies differ by stray whitespace
            # ("Schulabschluss:  Was" vs "Schulabschluss: Was").
            title_key = " ".join((c.title or "").split()).lower()
            if c.url in seen_urls or (title_key and title_key in seen_titles):
                continue
            seen_urls.add(c.url)
            if title_key:
                seen_titles.add(title_key)
            sources.append({"title": c.title, "url": c.url})
        if self._chunks:
            # Shows in Railway logs how often the model skips the QUELLEN line
            # (then every retrieved page is listed) and how much it filters.
            listed = "missing" if used is None else sorted(used)
            print(
                f"[sources] QUELLEN {listed} of {len(self._chunks)} blocks -> {len(sources)} pages",
                file=sys.stderr,
            )
        if self._authority is not None:
            authority_source = self._authority.source()
            sources = [s for s in sources if s["url"] != authority_source["url"]]
            sources.insert(0, authority_source)
        return answer, sources
