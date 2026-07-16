"""RAG pipeline: FAISS retrieval + LLM answer generation.

Index *building* lives in crawler/build_index.py; this module only *loads*
the already-built FAISS index and reads chunk metadata, read-only, at
startup (see CLAUDE.md on why these stay separate — under Railway, each
backend worker/replica loads the index independently).
"""

import os
from pathlib import Path

import faiss
import numpy as np
from openai import OpenAI

from app.db import SessionLocal
from app.models import Chunk
from behoerde import BehoerdeResult

REPO_ROOT = Path(__file__).resolve().parent.parent
EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"
TOP_K = 5

# Product positioning (see CLAUDE.md): translate Amtsdeutsch into plain
# language with actionable steps. The context is always German; the answer
# is written in the user's language.
SYSTEM_PROMPT = """\
Du bist ein Assistent, der deutsches Behördendeutsch in einfache Sprache übersetzt \
(Schwerpunkte: Bürgergeld/Grundsicherung, Kindergeld, Zuständigkeiten von Behörden).

Regeln:
- Antworte AUSSCHLIESSLICH auf Basis des gegebenen Kontexts. Wenn der Kontext die \
Antwort nicht enthält, sage das ehrlich und rate nicht.
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
    "uk": "українська",
    "ru": "русский",
    "pl": "polski",
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


class RAGPipeline:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self.index = faiss.read_index(str(resolve_faiss_path()))

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
