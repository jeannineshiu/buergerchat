"""Merges crawler JSONL outputs and builds the FAISS index + chunk metadata DB.

Per CLAUDE.md: index *building* is the crawler's job; the backend only
*loads* the index read-only at startup (backend/rag.py). This script is
meant to be re-run whenever crawler output changes — currently a manual
step, a Railway cron job later.

Defines its own local Chunk/DB schema instead of importing backend/app —
crawler and backend are independent modules with separate dependency sets
(see CLAUDE.md), so they agree on a schema rather than share code.
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import faiss
import numpy as np
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI, RateLimitError
from sqlalchemy import Column, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

REPO_ROOT = Path(__file__).resolve().parent.parent
CRAWLER_OUTPUT_DIR = REPO_ROOT / "crawler" / "output"
MERGED_OUTPUT_PATH = CRAWLER_OUTPUT_DIR / "merged.jsonl"

INPUT_FILES = [
    (CRAWLER_OUTPUT_DIR / "arbeitsagentur.jsonl", "arbeitsagentur"),
    (CRAWLER_OUTPUT_DIR / "gesetze.jsonl", "gesetze"),
    (CRAWLER_OUTPUT_DIR / "portal_familienportal.jsonl", "familienportal"),
    (CRAWLER_OUTPUT_DIR / "portal_bzst.jsonl", "bzst"),
    (CRAWLER_OUTPUT_DIR / "portal_drv.jsonl", "deutsche-rentenversicherung"),
    (CRAWLER_OUTPUT_DIR / "portal_bmwsb.jsonl", "bmwsb"),
    (CRAWLER_OUTPUT_DIR / "portal_bamf.jsonl", "bamf"),
    (CRAWLER_OUTPUT_DIR / "portal_berlin.jsonl", "service.berlin.de"),
    (CRAWLER_OUTPUT_DIR / "portal_elster.jsonl", "elster"),
]

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
EMBED_BATCH_SIZE = 100

SQLITE_PREFIX = "sqlite:///"

Base = declarative_base()


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True)
    url = Column(String, nullable=False)
    title = Column(String)
    topic = Column(String)
    source = Column(String)
    content = Column(Text, nullable=False)
    crawled_at = Column(String)


def resolve_database_url(url: str) -> str:
    if url.startswith(SQLITE_PREFIX):
        raw_path = url[len(SQLITE_PREFIX):]
        abs_path = (REPO_ROOT / raw_path).resolve()
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"{SQLITE_PREFIX}{abs_path}"
    return url


def resolve_faiss_path(raw_path: str) -> Path:
    path = (REPO_ROOT / raw_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_and_merge_records() -> list[dict]:
    records = []
    for path, source in INPUT_FILES:
        if not path.exists():
            print(f"[warn] {path.name} missing — skipping {source}", file=sys.stderr)
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                record["source"] = source
                records.append(record)

    with open(MERGED_OUTPUT_PATH, "w", encoding="utf-8") as out_file:
        for record in records:
            out_file.write(json.dumps(record, ensure_ascii=False) + "\n")

    return records


def chunk_records(records: list[dict]) -> list[dict]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = []
    for record in records:
        for piece in splitter.split_text(record["content"]):
            chunks.append(
                {
                    "url": record["url"],
                    "title": record.get("title", ""),
                    "topic": record.get("topic", ""),
                    "source": record["source"],
                    "content": piece,
                    "crawled_at": record.get("crawled_at", ""),
                }
            )
    return chunks


def dedupe_chunks(chunks: list[dict]) -> list[dict]:
    """Drop chunks whose content is byte-identical to an earlier one —
    e.g. arbeitsagentur.de syndicates the same article under multiple
    per-Ort URLs, so the same paragraph would otherwise get embedded and
    indexed once per syndicated copy. Keeps the first occurrence, so
    output stays deterministic for the same input (see
    test_chunking_is_deterministic)."""
    seen: set[str] = set()
    deduped = []
    for chunk in chunks:
        key = hashlib.sha256(chunk["content"].strip().encode("utf-8")).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(chunk)
    return deduped


def embed_texts(client: OpenAI, texts: list[str]) -> list[list[float]]:
    embeddings = []
    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[i : i + EMBED_BATCH_SIZE]
        # The corpus outgrew the 1M tokens/min embedding limit; the SDK's
        # built-in retries alone give up too early, so back off explicitly.
        for attempt in range(6):
            try:
                response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
                break
            except RateLimitError:
                if attempt == 5:
                    raise
                wait = 2 ** attempt * 5
                print(f"rate limited — waiting {wait}s", file=sys.stderr)
                time.sleep(wait)
        embeddings.extend(item.embedding for item in response.data)
        print(f"embedded {min(i + EMBED_BATCH_SIZE, len(texts))}/{len(texts)}")
    return embeddings


def write_metadata_db(database_url: str, chunks: list[dict]) -> None:
    engine = create_engine(database_url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    session = sessionmaker(bind=engine)()
    session.bulk_save_objects(
        [
            Chunk(
                id=i,
                url=c["url"],
                title=c["title"],
                topic=c["topic"],
                source=c["source"],
                content=c["content"],
                crawled_at=c["crawled_at"],
            )
            for i, c in enumerate(chunks)
        ]
    )
    session.commit()
    session.close()


def build_faiss_index(embeddings: list[list[float]]) -> faiss.Index:
    matrix = np.array(embeddings, dtype="float32")
    faiss.normalize_L2(matrix)  # inner product on normalized vectors == cosine similarity
    index = faiss.IndexIDMap(faiss.IndexFlatIP(EMBEDDING_DIM))
    ids = np.arange(len(embeddings), dtype="int64")
    index.add_with_ids(matrix, ids)
    return index


def main() -> None:
    load_dotenv(REPO_ROOT / "backend" / ".env")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit("OPENAI_API_KEY not set (checked backend/.env)")

    database_url = resolve_database_url(os.environ.get("DATABASE_URL", "sqlite:///data/metadata.db"))
    index_path = resolve_faiss_path(os.environ.get("FAISS_INDEX_PATH", "data/faiss_index.bin"))

    print("merging crawler output...")
    records = load_and_merge_records()
    print(f"{len(records)} raw records -> {MERGED_OUTPUT_PATH}")

    chunks = chunk_records(records)
    print(f"{len(chunks)} chunks after splitting (chunk_size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")

    deduped = dedupe_chunks(chunks)
    print(f"{len(deduped)} chunks after dedup ({len(chunks) - len(deduped)} duplicates dropped)")
    chunks = deduped

    client = OpenAI(api_key=api_key)
    embeddings = embed_texts(client, [c["content"] for c in chunks])

    print(f"writing metadata -> {database_url}")
    write_metadata_db(database_url, chunks)

    print(f"building FAISS index -> {index_path}")
    index = build_faiss_index(embeddings)
    faiss.write_index(index, str(index_path))

    print(f"done: {len(chunks)} vectors indexed")


if __name__ == "__main__":
    main()
