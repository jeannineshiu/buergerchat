"""RAG pipeline: FAISS retrieval + LLM answer generation.

Index *building* lives in crawler/build_index.py; this module only *loads*
the already-built FAISS index and reads chunk metadata, read-only, at
startup (see CLAUDE.md on why these stay separate — under Railway, each
backend worker/replica loads the index independently).
"""

import os
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
# gpt-4o-mini code-switched into German on zh-Hans answers; gpt-5.4-mini
# (A/B-tested 2026-07) keeps all 12 languages clean at similar latency.
CHAT_MODEL = os.environ.get("CHAT_MODEL", "gpt-5.4-mini")
TOP_K = 5

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
- Erwähne den "Kontext" gegenüber der Person NIE — das ist ein internes Detail. \
Sage stattdessen "nach den gesetzlichen Regelungen", "laut Bundesrecht" oder \
"nach den offiziellen Informationen". Statt "der Kontext enthält dazu nichts" \
sage "dazu liegen mir keine gesicherten Informationen vor".
- Wenn die Antwort eine PERSÖNLICHE Anspruchs- oder Berechtigungsfrage betrifft \
(z. B. Anspruch auf Bürgergeld, Niederlassungserlaubnis, Wohngeld), beende die \
Antwort mit einer direkten Empfehlung in dieser Form: "Um Ihre persönliche \
Situation zu klären, wenden Sie sich an [zuständige Stelle]." — als Aussage, \
nicht als Frage ("falls Sie möchten" o. Ä. ist verboten).
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
(steht am Ende der Nachricht). Amtliche Begriffe und Behördennamen bleiben auf \
Deutsch, mit kurzer Erklärung in der Antwortsprache.\
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


def language_directive(language: str) -> str:
    name = LANGUAGE_NAMES.get(language, language)
    if language == "de":
        return "Antworte auf Deutsch."
    return (
        f"IMPORTANT: Write your entire answer in {name} (language code: {language}), "
        f"NOT in German. Keep official German terms in German, each with a short "
        f"explanation in {name}."
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

    def query(
        self,
        message: str,
        language: str = "de",
        topic: str | None = None,
        authority: BehoerdeResult | None = None,
        ask_for_plz: bool = False,
        authority_missing: bool = False,
        history: list[dict] | None = None,
    ):
        self._ensure_loaded()
        embed_response = self.client.embeddings.create(model=EMBEDDING_MODEL, input=message)
        query_vector = np.array([embed_response.data[0].embedding], dtype="float32")
        faiss.normalize_L2(query_vector)

        _, ids = self.index.search(query_vector, TOP_K)
        hit_ids = [int(i) for i in ids[0] if i != -1]

        session = SessionLocal()
        chunks_by_id = {c.id: c for c in session.query(Chunk).filter(Chunk.id.in_(hit_ids)).all()}
        session.close()
        ordered_chunks = [chunks_by_id[i] for i in hit_ids if i in chunks_by_id]

        context_text = "\n\n".join(f"[{c.title}]\n{c.content}" for c in ordered_chunks)
        if authority is not None:
            context_text = (
                "[Zuständige Stelle laut Behördenfinder (PVOG)]\n"
                f"{authority.context_block()}\n\n{context_text}"
            )

        directives = [language_directive(language)]
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
        completion = self.client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *history_messages,
                {
                    "role": "user",
                    "content": f"Kontext:\n{context_text}\n\nFrage: {message}\n\n"
                    + "\n".join(directives),
                },
            ],
        )
        answer = completion.choices[0].message.content

        sources = [{"title": c.title, "url": c.url} for c in ordered_chunks]
        if authority is not None:
            sources.insert(0, authority.source())
        return answer, sources
