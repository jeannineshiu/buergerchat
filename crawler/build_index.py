"""Merges crawler JSONL outputs and builds the FAISS index + chunk metadata DB.

Per CLAUDE.md: index *building* is the crawler's job; the backend only
*loads* the index read-only at startup (backend/rag.py). This script is
meant to be re-run whenever crawler output changes — currently a manual
step, a Railway cron job later.

Embeddings are reused from the previous build: a chunk whose content is
byte-identical to one in the existing data/ index keeps that vector, so
only new or changed chunks cost an OpenAI call. When the chunk list is
identical to the previous build, nothing is written at all (and nothing
needs a redeploy). `--full` re-embeds everything — required after
changing EMBEDDING_MODEL, since the previous build does not record which
model made its vectors.

Defines its own local Chunk/DB schema instead of importing backend/app —
crawler and backend are independent modules with separate dependency sets
(see CLAUDE.md), so they agree on a schema rather than share code.
"""

import argparse
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
from sqlalchemy import Column, Integer, String, Text, create_engine, inspect
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


def content_key(content: str) -> str:
    return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()


CHUNK_FIELDS = ("url", "title", "topic", "source", "content", "crawled_at")


def chunk_row(chunk: dict) -> tuple:
    return tuple(chunk[field] for field in CHUNK_FIELDS)


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
        key = content_key(chunk["content"])
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


def load_previous_build(database_url: str, index_path: Path) -> tuple[list[tuple], dict[str, np.ndarray]]:
    """Chunk rows (in id order) and content_key -> vector of the existing
    build, or ([], {}) when there is none or it is inconsistent. Chunk id ==
    FAISS id == position (see build_faiss_index), so the i-th stored vector
    belongs to the i-th row."""
    if not index_path.exists():
        return [], {}
    engine = create_engine(database_url)
    try:
        if not inspect(engine).has_table(Chunk.__tablename__):
            return [], {}
        session = sessionmaker(bind=engine)()
        chunks = session.query(Chunk).order_by(Chunk.id).all()
        rows = [tuple(getattr(c, field) for field in CHUNK_FIELDS) for c in chunks]
        ids = [c.id for c in chunks]
        session.close()
    finally:
        engine.dispose()

    index = faiss.read_index(str(index_path))
    if index.d != EMBEDDING_DIM or index.ntotal != len(rows) or ids != list(range(len(rows))):
        print("[warn] previous index does not match its metadata — re-embedding everything", file=sys.stderr)
        return [], {}
    # IndexIDMap cannot reconstruct by id; the wrapped flat index stores
    # the vectors in insertion order, which is id order here.
    vectors = faiss.downcast_index(index.index).reconstruct_n(0, index.ntotal)
    content_idx = CHUNK_FIELDS.index("content")
    return rows, {content_key(row[content_idx]): vectors[i] for i, row in enumerate(rows)}


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
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="re-embed every chunk instead of reusing the previous build's vectors")
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / "backend" / ".env")

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

    previous_rows, previous_vectors = ([], {}) if args.full else load_previous_build(database_url, index_path)
    if previous_rows and previous_rows == [chunk_row(c) for c in chunks]:
        print("unchanged since the previous build — nothing written")
        return

    to_embed = [c for c in chunks if content_key(c["content"]) not in previous_vectors]
    print(f"{len(chunks) - len(to_embed)} embeddings reused, {len(to_embed)} to embed")
    new_vectors = {}
    if to_embed:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            sys.exit("OPENAI_API_KEY not set (checked backend/.env)")
        client = OpenAI(api_key=api_key)
        embedded = embed_texts(client, [c["content"] for c in to_embed])
        new_vectors = {content_key(c["content"]): v for c, v in zip(to_embed, embedded)}
    vectors = previous_vectors | new_vectors
    embeddings = [vectors[content_key(c["content"])] for c in chunks]

    print(f"writing metadata -> {database_url}")
    write_metadata_db(database_url, chunks)

    print(f"building FAISS index -> {index_path}")
    index = build_faiss_index(embeddings)
    faiss.write_index(index, str(index_path))

    print(f"done: {len(chunks)} vectors indexed")


if __name__ == "__main__":
    main()
