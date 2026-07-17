"""RAGPipeline with a real (tiny) FAISS index in the temp DATA_DIR and a
fake OpenAI client — exercises lazy loading, retrieval wiring, prompt
assembly and source ordering without network."""

import faiss
import numpy as np
import pytest

import rag
from behoerde import BehoerdeResult
from rag import IndexNotReadyError, RAGPipeline, language_directive, resolve_faiss_path

CHUNKS = [
    (0, "Bürgergeld ist eine Leistung des Jobcenters."),
    (1, "Kindergeld beantragt man bei der Familienkasse."),
    (2, "Wohngeld ist ein Zuschuss zur Miete."),
]


@pytest.fixture()
def pipeline(data_dir, fake_openai, monkeypatch):
    # Write chunks into the metadata DB the app engine points at.
    from app.db import Base, SessionLocal, engine
    from app.models import Chunk

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session = SessionLocal()
    for cid, text in CHUNKS:
        session.add(Chunk(id=cid, url=f"https://example.org/{cid}", title=f"Doc {cid}", content=text))
    session.commit()
    session.close()

    # Build the FAISS index from the same fake embeddings the query will use.
    vectors = np.array(
        [fake_openai.embeddings.create(model="x", input=text).data[0].embedding for _, text in CHUNKS],
        dtype="float32",
    )
    faiss.normalize_L2(vectors)
    index = faiss.IndexIDMap(faiss.IndexFlatIP(1536))
    index.add_with_ids(vectors, np.array([cid for cid, _ in CHUNKS], dtype="int64"))
    faiss.write_index(index, str(data_dir / "faiss_index.bin"))

    monkeypatch.setattr(rag, "TOP_K", 2)
    p = RAGPipeline()
    p.client = fake_openai
    return p


class TestLazyLoading:
    def test_init_does_not_touch_index_file(self, fake_openai):
        p = RAGPipeline()
        p.client = fake_openai
        assert p.index is None and not p.index_loaded

    def test_query_raises_when_index_missing(self, data_dir, fake_openai):
        index_file = data_dir / "faiss_index.bin"
        if index_file.exists():
            index_file.unlink()
        p = RAGPipeline()
        p.client = fake_openai
        with pytest.raises(IndexNotReadyError):
            p.query("Was ist Bürgergeld?")
        assert p.load() is False

    def test_load_succeeds_once_file_appears(self, pipeline):
        assert pipeline.load() is True
        assert pipeline.index_loaded


class TestQuery:
    def test_retrieves_matching_chunk_as_source(self, pipeline):
        answer, sources = pipeline.query("Bürgergeld ist eine Leistung des Jobcenters.")
        assert answer == "STUB ANSWER"
        assert sources[0]["url"] == "https://example.org/0"

    def test_authority_becomes_first_source_and_context_block(self, pipeline):
        authority = BehoerdeResult(
            authority_name="Jobcenter Test", service_name="Bürgergeld", website="https://jc.example"
        )
        _, sources = pipeline.query("Bürgergeld", authority=authority)
        assert sources[0] == {"title": "Jobcenter Test — Bürgergeld", "url": "https://jc.example"}
        prompt = pipeline.client.chat.completions.last_messages[-1]["content"]
        assert "Zuständige Stelle laut Behördenfinder (PVOG)" in prompt

    def test_meta_only_skips_retrieval_and_sources(self, pipeline):
        answer, sources = pipeline.query("Was kannst du?", meta_only=True)
        assert answer == "STUB ANSWER"
        assert sources == []

    def test_history_is_passed_and_truncated(self, pipeline):
        history = [{"role": "user", "content": f"msg{i}"} for i in range(10)]
        pipeline.query("Bürgergeld", history=history)
        messages = pipeline.client.chat.completions.last_messages
        history_contents = [m["content"] for m in messages if m["content"].startswith("msg")]
        assert history_contents == [f"msg{i}" for i in range(4, 10)]  # last 6

    def test_ask_for_plz_directive_in_prompt(self, pipeline):
        pipeline.query("Wo ist mein Jobcenter?", ask_for_plz=True)
        prompt = pipeline.client.chat.completions.last_messages[-1]["content"]
        assert "Postleitzahl" in prompt

    def test_authority_missing_directive_forbids_invention(self, pipeline):
        pipeline.query("Wo ist mein Jobcenter?", authority_missing=True)
        prompt = pipeline.client.chat.completions.last_messages[-1]["content"]
        assert "ERFINDE KEINE" in prompt


class TestHelpers:
    def test_language_directive_german_is_plain(self):
        assert language_directive("de") == "Antworte auf Deutsch."

    def test_language_directive_other_language_names_it(self):
        directive = language_directive("zh-Hant")
        assert "繁體中文" in directive and "NOT in German" in directive

    def test_resolve_faiss_path_uses_data_dir(self, data_dir):
        assert resolve_faiss_path() == (data_dir / "faiss_index.bin").resolve()

    def test_explicit_faiss_index_path_wins(self, monkeypatch, tmp_path):
        custom = tmp_path / "custom.bin"
        monkeypatch.setenv("FAISS_INDEX_PATH", str(custom))
        assert resolve_faiss_path() == custom.resolve()
