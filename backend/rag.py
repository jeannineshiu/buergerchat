"""RAG pipeline: FAISS retrieval + LLM answer generation.

Index *building* lives in crawler/build_index.py; this module only *loads*
the already-built FAISS index and reads chunk metadata, read-only, at
startup (see CLAUDE.md on why these stay separate — under Railway, each
backend worker/replica loads the index independently).
"""

import os
import re
import threading
from pathlib import Path

import faiss
import numpy as np
from openai import OpenAI

from app.db import SessionLocal
from app.models import Chunk
from behoerde import BehoerdeResult

REPO_ROOT = Path(__file__).resolve().parent.parent
EMBEDDING_MODEL = "text-embedding-3-small"
# Model history (all A/B-tested on zh answers): gpt-4o-mini code-switched
# German into zh-Hans; gpt-5.4-mini fixed that but kept ending answers with
# "if you want, I can …" offers despite explicit bans (2/4 runs); the
# chat-tuned gpt-5.3-chat-latest follows the style rules (0/4). It is an
# unpinned alias — if behavior shifts after an OpenAI update, re-run the
# style checks and adjust via the CHAT_MODEL env var.
CHAT_MODEL = os.environ.get("CHAT_MODEL", "gpt-5.3-chat-latest")
TOP_K = 5

# Vector similarity alone cannot separate the answer from the noise on
# amount questions: for "Wie hoch ist der Regelsatz beim Bürgergeld für
# Alleinstehende?" the 30 nearest chunks span cosine 0.639..0.578, the top 5
# are Elterngeld/Kinderzuschlag pages, and the chunk that actually states
# "Regelbedarf (alleinstehende Person) 563,00 Euro" sits at rank 21. So embed
# wide, then let a model read the candidates and pick. Three other chunks in
# that window also carry a 5xx € figure while answering a different question,
# which is why pure keyword fusion (FTS5+RRF) net-hurt recall and was reverted.
CANDIDATE_K = int(os.environ.get("CANDIDATE_K", "30"))
# DEFAULT OFF. The first iteration *replaced* the vector top-5 with the
# reranker's picks; that fixed the Regelsatz case (the 563-Euro chunk went
# from rank 21 to rank 1) but was zero-sum — with exactly TOP_K chunks
# reaching the answer, promoting the chunk with the requested figure could
# only evict a definitional chunk the eval counts as relevant (recall@5
# de/en 95->89%, 2026-08-09). So reranking now *augments* instead: the
# vector top-K is kept untouched and up to RERANK_EXTRA_K reranker picks
# that aren't already in it are appended. Existing hits can no longer be
# lost, at the cost of a longer answer context and one extra chat call per
# query. Golden-set A/B 2026-08-09 (19 items): recall de 95->100%,
# en 95->100%, zh-Hant 95->95% (k=5 -> k=5-8); it repaired
# kindergeld-rueckwirkend [en] and arbeitsuchend-frist [de], broke nothing,
# and left only steuerid-wo [zh-Hant] missing. Set RERANK=1 to enable.
RERANK = os.environ.get("RERANK", "0").lower() not in ("0", "false", "no")
RERANK_MODEL = os.environ.get("RERANK_MODEL", CHAT_MODEL)
# How many reranker picks may join the vector top-K in the answer context.
RERANK_EXTRA_K = int(os.environ.get("RERANK_EXTRA_K", "3"))
# Enough of a chunk to judge relevance without paying for all 30 in full.
RERANK_SNIPPET_CHARS = 600

RERANK_PROMPT = """\
Du bewertest Textausschnitte aus offiziellen deutschen Behörden- und \
Gesetzestexten danach, ob sie eine konkrete Nutzerfrage beantworten.

Wähle die {top_k} Ausschnitte, die die Frage am direktesten beantworten. \
Ein Ausschnitt, der die gefragte Zahl, Frist oder Bedingung ausdrücklich \
nennt, ist besser als einer, der nur dasselbe Thema streift. Ausschnitte \
mit einer Zahl zu einer ANDEREN Leistung sind nicht relevant.

Antworte ausschließlich mit den Nummern, absteigend nach Nützlichkeit, \
durch Komma getrennt. Keine Erklärung. Beispiel: 7,2,15,1,9"""

# Product positioning (see CLAUDE.md): translate Amtsdeutsch into plain
# language with actionable steps. The context is always German; the answer
# is written in the user's language.
SYSTEM_PROMPT = """\
Du bist ein Assistent, der deutsches Behördendeutsch in einfache Sprache übersetzt \
(Schwerpunkte: Bürgergeld/Grundsicherung, Kindergeld und Familienleistungen, Rente, \
Wohngeld, Steuer-ID und Steuern, Aufenthalt und Einbürgerung, Zuständigkeiten von Behörden).

Regeln:
- Antworte AUSSCHLIESSLICH auf Basis des gegebenen Kontexts. Wenn der Kontext die \
Antwort nicht enthält, sage das ehrlich und rate nicht.
- META-FRAGEN: Fragt die Person, was du kannst oder welche Fragen sie dir stellen \
kann, ignoriere den Kontext VOLLSTÄNDIG (er ist dann zufällig und irrelevant) und \
nenne genau diese Themen, ohne weitere hinzuzuerfinden: Bürgergeld/Grundsicherungsgeld, \
Kindergeld und Familienleistungen, Arbeitslosengeld, Rente, Wohngeld, Steuer-ID und \
Steuern, Aufenthalt und Einbürgerung — und dass du die zuständige Behörde findest, \
wenn die Person ihre Postleitzahl nennt. Danach lade zur konkreten Frage ein. Keine \
Zitate oder Beispiele aus dem Kontext in dieser Antwort.
- Erwähne den "Kontext" gegenüber der Person NIE — das ist ein internes Detail. \
Sage stattdessen "nach den gesetzlichen Regelungen", "laut Bundesrecht" oder \
"nach den offiziellen Informationen". Statt "der Kontext enthält dazu nichts" \
sage "dazu liegen mir keine gesicherten Informationen vor".
- Wenn du eine Frage NICHT beantworten kannst (keine gesicherten Informationen), \
ergänze nach dem ehrlichen Hinweis genau einen Satz dazu, wobei du helfen kannst: \
Bürgergeld/Grundsicherungsgeld, Kindergeld und Familienleistungen, Arbeitslosengeld, \
Rente, Wohngeld, Steuer-ID, Aufenthalt und Einbürgerung sowie die Suche nach der \
zuständigen Behörde (mit Postleitzahl).
- Wenn die Antwort eine PERSÖNLICHE Anspruchs- oder Berechtigungsfrage betrifft \
(z. B. Anspruch auf Bürgergeld, Niederlassungserlaubnis, Wohngeld), beende die \
Antwort mit einer direkten Empfehlung nach dem Muster "Um Ihre persönliche \
Situation zu klären, wenden Sie sich an [zuständige Stelle]." — als Aussage, \
nicht als Frage ("falls Sie möchten" o. Ä. ist verboten), und IMMER in der \
Antwortsprache formuliert (nur der Behördenname bleibt Deutsch).
- Wenn bei einer Anspruchsfrage eine entscheidende Angabe der Person offensichtlich \
fehlt (z. B. Art des Aufenthaltstitels, Beschäftigungsstatus, Einkommen), stelle \
am Ende GENAU EINE gezielte Rückfrage nach der wichtigsten fehlenden Angabe und \
erkläre kurz, warum sie wichtig ist — z. B.: "Welche Art von Aufenthaltstitel \
haben Sie derzeit? Davon hängt ab, was für Sie gilt."
- Schreibe in einfacher Sprache (Niveau B1): kurze Sätze, keine Amtssprache. \
Nenne amtliche Begriffe trotzdem beim Namen (z. B. "Bedarfsgemeinschaft"), aber \
erkläre sie sofort in einfachen Worten.
- Wenn der Kontext einen Abschnitt "[Zuständige Stelle laut Behördenfinder (PVOG)]" \
enthält, nenne diese Stelle in der Antwort ausdrücklich mit Name, Adresse und \
Kontaktmöglichkeiten — das ist die konkrete Anlaufstelle für die Person.
- Mache die Antwort handlungsorientiert. Wenn es zur Frage passt, nenne: \
Wer hat Anspruch? Was muss man konkret tun? Welche Behörde ist zuständig \
(z. B. Familienkasse für Kindergeld, Jobcenter für Bürgergeld/Grundsicherung)?
- Hinweis zur Übergangszeit: "Bürgergeld" heißt seit dem 1. Juli 2026 \
"Grundsicherungsgeld" (Neue Grundsicherung). Beide Begriffe meinen dieselbe Leistung; \
erwähne das kurz, wenn die Frage eine der beiden Bezeichnungen verwendet.
- Der Kontext ist immer auf Deutsch. Antworte in der vom Nutzer gewünschten Sprache \
(steht am Ende der Nachricht). NUR amtliche Begriffe und Eigennamen (Substantive wie \
"Familienkasse", "Steuer-Identifikationsnummer") bleiben auf Deutsch, mit kurzer \
Erklärung in der Antwortsprache — deutsche Adjektive und Satzteile (z. B. \
"zuständige") werden übersetzt, nie mit dem Zielsprachtext verklebt. Außer diesen \
Begriffen darf KEIN Wort einer anderen Sprache in der Antwort vorkommen.
- Nenne konkrete Voraussetzungen (wer, ab wann, unter welchen Bedingungen). \
Zirkelaussagen wie "Anspruch hat, wer berechtigt ist" sind verboten — wenn der \
Kontext nichts Konkreteres hergibt, lass den Punkt weg.
- Beende die Antwort NIE mit Angeboten wie "wenn Sie möchten, kann ich …" oder \
"soll ich Ihnen …?". Liefere nützliche Zusatzinformation direkt oder lass sie weg. \
Die einzige erlaubte Rückfrage ist die eine gezielte Frage nach einer fehlenden \
entscheidenden Angabe (siehe oben) — formuliere sie DIREKT und ohne Anbieterfloskel: \
"Nennen Sie mir Ihre Postleitzahl, dann nenne ich Ihnen Ihre Familienkasse." \
statt "Wenn Sie möchten, kann ich Ihnen Ihre Familienkasse finden."\
"""

# The language directive lives at the END of the user message, not only in the
# system prompt: with an all-German prompt+context, gpt-4o-mini otherwise
# drifts back to German (observed with language="en").
LANGUAGE_NAMES = {
    "de": "Deutsch",
    "en": "English",
    "tr": "Türkçe",
    "ar": "العربية",
    "fa": "فارسی",
    "uk": "українська",
    "ru": "русский",
    "pl": "polski",
    "zh-Hant": "繁體中文 (Traditional Chinese)",
    "zh-Hans": "简体中文 (Simplified Chinese)",
    "vi": "Tiếng Việt",
    "id": "Bahasa Indonesia",
    "ko": "한국어 (Korean)",
}


# The corpus is 100% German; text-embedding-3-small only aligns German
# and English queries with it well (evals, recall@5: de 89%, en 100%,
# but tr/pl/vi/id 68% and zh-Hant 68% pre-translation). Every query that
# is (probably) neither German nor English is translated to German
# before embedding — non-Latin scripts are detected from the text, the
# Latin-script languages via the request's answer language.
NON_LATIN_QUERY = re.compile(
    "[Ѐ-ӿ"   # Cyrillic
    "֐-׿"    # Hebrew
    "؀-ۿ"    # Arabic
    "぀-ヿ"    # Kana
    "一-鿿"    # CJK
    "가-힯]"   # Hangul
)

TRANSLATE_PROMPT = (
    "Übersetze die folgende Nutzerfrage zu deutschen Behörden und "
    "Sozialleistungen ins Deutsche, für eine Dokumentensuche. Amtliche "
    "deutsche Begriffe (Kindergeld, Jobcenter …) unverändert lassen. "
    "Gib NUR die deutsche Übersetzung aus, nichts anderes."
)


def language_directive(language: str) -> str:
    name = LANGUAGE_NAMES.get(language, language)
    if language == "de":
        return "Antworte auf Deutsch."
    return (
        f"IMPORTANT: Write your entire answer in {name} (language code: {language}), "
        f"NOT in German. Keep official German terms (nouns/proper names only) in "
        f"German, each with a short explanation in {name}. Except for those terms, "
        f"every single word must be {name} — never mix in any third language."
    )


# Scripts that are legitimate in NONE of the 13 answer languages (which use
# Latin, Arabic, Cyrillic, Han and Hangul). Both gpt-5.3 and gpt-5.4-mini
# occasionally leak e.g. Thai "ย้อนหลัง" into Chinese answers — always at the
# same semantic spot ("retroactive"). One corrective retry fixes it.
FORBIDDEN_SCRIPTS = re.compile(
    "[԰-֏"   # Armenian
    "֐-׿"    # Hebrew
    "ހ-޿"    # Thaana
    "ऀ-෿"    # Devanagari … Sinhala (Indic block run)
    "฀-໿"    # Thai, Lao
    "က-႟"    # Myanmar
    "Ⴀ-ჿ"    # Georgian
    "ሀ-፿"    # Ethiopic
    "ក-៿"    # Khmer
    "぀-ヿ]"   # Hiragana, Katakana
)


def resolve_faiss_path() -> Path:
    # DATA_DIR points at the built artifacts (on Railway: the volume mount,
    # /data). Relative values are anchored to the repo root per the path
    # convention; absolute ones pass through (REPO_ROOT / "/data" == "/data").
    explicit = os.environ.get("FAISS_INDEX_PATH")
    if explicit:
        return (REPO_ROOT / explicit).resolve()
    data_dir = os.environ.get("DATA_DIR", "data")
    return (REPO_ROOT / data_dir / "faiss_index.bin").resolve()


class IndexNotReadyError(Exception):
    """The FAISS index file is not (yet) present — e.g. a fresh Railway
    deploy whose /data volume hasn't been populated."""


class RAGPipeline:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        # Lazy: the index is loaded on first use (or explicit load()), not at
        # import time, so the app can start before the volume is populated.
        self.index = None
        self._load_lock = threading.Lock()

    @property
    def index_loaded(self) -> bool:
        return self.index is not None

    def load(self) -> bool:
        """Load the FAISS index if the file exists. Returns True when the
        index is available (already loaded or loaded now)."""
        if self.index is not None:
            return True
        with self._load_lock:
            if self.index is None:
                path = resolve_faiss_path()
                if not path.exists():
                    return False
                self.index = faiss.read_index(str(path))
        return True

    def _ensure_loaded(self):
        if not self.load():
            raise IndexNotReadyError(str(resolve_faiss_path()))

    def _query_to_german(self, query: str) -> str:
        """Translate a non-Latin-script query to German for retrieval.
        Any failure falls back to the original query — retrieval quality
        degrades, but /chat keeps working."""
        try:
            response = self.client.chat.completions.create(
                model=CHAT_MODEL,
                messages=[
                    {"role": "system", "content": TRANSLATE_PROMPT},
                    {"role": "user", "content": query},
                ],
            )
            translated = (response.choices[0].message.content or "").strip()
            return translated or query
        except Exception:
            return query

    def _rerank(self, query: str, candidates: list[Chunk]) -> list[Chunk]:
        """Ask a model which candidates answer the query; return its picks
        in model order.

        Any failure — API error, unparseable reply, indices out of range —
        returns [], so retrieval degrades to the plain vector top-K instead
        of breaking /chat.
        """
        listing = "\n\n".join(
            f"[{n}] {chunk.title}\n{chunk.content[:RERANK_SNIPPET_CHARS]}"
            for n, chunk in enumerate(candidates, 1)
        )
        try:
            response = self.client.chat.completions.create(
                model=RERANK_MODEL,
                messages=[
                    {"role": "system", "content": RERANK_PROMPT.format(top_k=TOP_K)},
                    {"role": "user", "content": f"Frage: {query}\n\nAusschnitte:\n{listing}"},
                ],
            )
            reply = response.choices[0].message.content or ""
        except Exception:
            return []

        picked: list[Chunk] = []
        seen: set[int] = set()
        for number in re.findall(r"\d+", reply):
            index = int(number) - 1
            if 0 <= index < len(candidates) and index not in seen:
                seen.add(index)
                picked.append(candidates[index])
        return picked

    def retrieve(self, query: str, language: str = "de") -> list[Chunk]:
        """Embed the query and return the best chunks in rank order — the
        exact retrieval path /chat uses (evals reuse it). Plain vector
        top-K by default; with RERANK on, the vector search casts a wider
        net (CANDIDATE_K) and up to RERANK_EXTRA_K model-picked chunks are
        appended after the untouched vector top-K."""
        self._ensure_loaded()
        if NON_LATIN_QUERY.search(query) or language not in ("de", "en"):
            query = self._query_to_german(query)
        embed_response = self.client.embeddings.create(
            model=EMBEDDING_MODEL, input=query
        )
        query_vector = np.array([embed_response.data[0].embedding], dtype="float32")
        faiss.normalize_L2(query_vector)

        search_k = max(CANDIDATE_K, TOP_K) if RERANK else TOP_K
        _, ids = self.index.search(query_vector, search_k)
        hit_ids = [int(i) for i in ids[0] if i != -1]

        session = SessionLocal()
        chunks_by_id = {c.id: c for c in session.query(Chunk).filter(Chunk.id.in_(hit_ids)).all()}
        session.close()
        candidates = [chunks_by_id[i] for i in hit_ids if i in chunks_by_id]

        head = candidates[:TOP_K]
        if not RERANK or len(candidates) <= TOP_K:
            return head
        head_ids = {c.id for c in head}
        extras = [c for c in self._rerank(query, candidates) if c.id not in head_ids]
        return head + extras[:RERANK_EXTRA_K]

    def query(
        self,
        message: str,
        language: str = "de",
        topic: str | None = None,
        authority: BehoerdeResult | None = None,
        ask_for_plz: bool = False,
        authority_missing: bool = False,
        history: list[dict] | None = None,
        meta_only: bool = False,
        chitchat: bool = False,
        retrieval_query: str | None = None,
    ):
        # Capability meta-questions and pure small talk both skip retrieval:
        # random chunks would leak into the answer and the source list (see
        # META rule in the system prompt, and the chitchat directive below).
        ordered_chunks = []
        if not meta_only and not chitchat:
            # retrieval_query: follow-ups like "say that in Chinese" carry no
            # searchable meaning of their own — the caller passes a query
            # enriched with the previous question instead.
            ordered_chunks = self.retrieve(retrieval_query or message, language=language)

        context_text = "\n\n".join(f"[{c.title}]\n{c.content}" for c in ordered_chunks)
        if authority is not None:
            context_text = (
                "[Zuständige Stelle laut Behördenfinder (PVOG)]\n"
                f"{authority.context_block()}\n\n{context_text}"
            )

        # End-of-message directives bind harder than system-prompt rules for
        # this model (same reason language_directive lives here): the offer
        # endings and third-language leaks survived system-prompt-only bans.
        directives = [
            language_directive(language),
            "Do NOT end your answer with an offer such as 'if you want, I can …' "
            "(如果您要 / wenn Sie möchten / etc.). Include useful extra information "
            "directly, or end with ONE direct request for a missing fact, e.g. "
            "'Tell me your postal code and I will name your Familienkasse.' "
            "Double-check before finishing: every word is either the answer "
            "language or an official German term — no other language.",
        ]
        if chitchat:
            directives.append(
                "Die Nachricht ist reiner Small Talk (Begrüßung, Dank oder "
                "Verabschiedung) ohne inhaltliche Frage. Antworte NUR mit "
                "einem kurzen, freundlichen Satz in der Antwortsprache — "
                "ohne Bezug zum Kontext, ohne Rückfrage, ohne Aufzählung "
                "von Themen."
            )
        if ask_for_plz:
            directives.append(
                "Die Person möchte wissen, welche Stelle zuständig ist, hat aber "
                "keinen Ort genannt. Bitte sie (in der Antwortsprache) um ihre "
                "Postleitzahl, damit du die zuständige Stelle nennen kannst."
            )
        if authority_missing:
            directives.append(
                "Die zuständige Stelle konnte nicht automatisch ermittelt werden. "
                "ERFINDE KEINE Adressen oder Telefonnummern. Verweise die Person "
                "stattdessen auf https://servicesuche.bund.de/ zur Suche der "
                "zuständigen Stelle."
            )

        # The last ~3 exchanges give follow-ups like a bare "10115" their
        # context; older turns add cost without adding grounding.
        history_messages = [
            {"role": m["role"], "content": m["content"]} for m in (history or [])[-6:]
        ]
        messages_payload = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *history_messages,
            {
                "role": "user",
                "content": f"Kontext:\n{context_text}\n\nFrage: {message}\n\n"
                + "\n".join(directives),
            },
        ]
        completion = self.client.chat.completions.create(
            model=CHAT_MODEL, messages=messages_payload
        )
        answer = completion.choices[0].message.content

        leak = FORBIDDEN_SCRIPTS.search(answer or "")
        if leak:
            # One corrective retry; if the model leaks again, ship the retry
            # anyway — a rare stray word beats an error.
            snippet = answer[max(0, leak.start() - 10) : leak.start() + 10]
            retry = self.client.chat.completions.create(
                model=CHAT_MODEL,
                messages=messages_payload
                + [
                    {"role": "assistant", "content": answer},
                    {
                        "role": "user",
                        "content": "Your answer mixes in another language "
                        f"(near: {snippet!r}). Rewrite the ENTIRE answer using only "
                        "the requested answer language plus official German terms.",
                    },
                ],
            )
            answer = retry.choices[0].message.content

        # Several of the top-K chunks often come from the same (long) page —
        # fine for the context, but the visible source list should name each
        # page once, in retrieval order. Titles dedupe too: arbeitsagentur.de
        # syndicates the same article under per-Ort URLs.
        sources = []
        seen_urls: set[str] = set()
        seen_titles: set[str] = set()
        for c in ordered_chunks:
            # Normalized title: syndicated copies differ by stray whitespace
            # ("Schulabschluss:  Was" vs "Schulabschluss: Was").
            title_key = " ".join((c.title or "").split()).lower()
            if c.url in seen_urls or (title_key and title_key in seen_titles):
                continue
            seen_urls.add(c.url)
            if title_key:
                seen_titles.add(title_key)
            sources.append({"title": c.title, "url": c.url})
        if authority is not None:
            authority_source = authority.source()
            sources = [s for s in sources if s["url"] != authority_source["url"]]
            sources.insert(0, authority_source)
        return answer, sources
