import json

import pytest

import build_index


class TestChunkRecords:
    def test_short_record_is_single_chunk_with_metadata(self):
        records = [{
            "url": "https://x.de/a", "title": "T", "topic": "wohngeld",
            "source": "bmwsb", "content": "Kurzer Text.", "crawled_at": "2026-07-17",
        }]
        chunks = build_index.chunk_records(records)
        assert len(chunks) == 1
        assert chunks[0]["url"] == "https://x.de/a"
        assert chunks[0]["topic"] == "wohngeld"
        assert chunks[0]["source"] == "bmwsb"

    def test_long_record_is_split_with_overlap(self):
        text = " ".join(f"wort{i}" for i in range(1000))
        records = [{"url": "u", "title": "", "topic": "", "source": "s", "content": text}]
        chunks = build_index.chunk_records(records)
        assert len(chunks) > 1
        assert all(len(c["content"]) <= build_index.CHUNK_SIZE for c in chunks)

    def test_chunking_is_deterministic(self):
        # The chunk sequence doubles as the FAISS vector id sequence, and
        # metadata.db can be rebuilt from merged.jsonl without re-embedding
        # ONLY because this is deterministic.
        text = " ".join(f"wort{i}" for i in range(500))
        records = [{"url": "u", "title": "", "topic": "", "source": "s", "content": text}]
        assert build_index.chunk_records(records) == build_index.chunk_records(records)


class TestDedupeChunks:
    def test_identical_content_keeps_first_occurrence(self):
        chunks = [
            {"url": "https://x.de/a", "content": "Gleicher Text."},
            {"url": "https://x.de/b", "content": "Gleicher Text."},
        ]
        deduped = build_index.dedupe_chunks(chunks)
        assert len(deduped) == 1
        assert deduped[0]["url"] == "https://x.de/a"

    def test_distinct_content_all_kept(self):
        chunks = [
            {"url": "https://x.de/a", "content": "Text A."},
            {"url": "https://x.de/b", "content": "Text B."},
        ]
        assert build_index.dedupe_chunks(chunks) == chunks

    def test_whitespace_only_difference_is_still_a_duplicate(self):
        chunks = [
            {"url": "https://x.de/a", "content": "Text.  "},
            {"url": "https://x.de/b", "content": "Text."},
        ]
        assert len(build_index.dedupe_chunks(chunks)) == 1


class TestLoadAndMerge:
    def test_missing_input_files_are_skipped(self, tmp_path, monkeypatch, capsys):
        existing = tmp_path / "a.jsonl"
        existing.write_text(json.dumps({"url": "u", "content": "c"}) + "\n")
        monkeypatch.setattr(build_index, "INPUT_FILES", [
            (existing, "a"),
            (tmp_path / "missing.jsonl", "b"),
        ])
        monkeypatch.setattr(build_index, "MERGED_OUTPUT_PATH", tmp_path / "merged.jsonl")
        records = build_index.load_and_merge_records()
        assert len(records) == 1
        assert records[0]["source"] == "a"
        assert "missing" in capsys.readouterr().err

    def test_source_field_is_stamped(self, tmp_path, monkeypatch):
        f = tmp_path / "x.jsonl"
        f.write_text(json.dumps({"url": "u", "content": "c"}) + "\n")
        monkeypatch.setattr(build_index, "INPUT_FILES", [(f, "stamped-source")])
        monkeypatch.setattr(build_index, "MERGED_OUTPUT_PATH", tmp_path / "merged.jsonl")
        records = build_index.load_and_merge_records()
        assert records[0]["source"] == "stamped-source"


class TestBuildFaissIndex:
    def test_ids_map_to_positions(self):
        import numpy as np

        rng = np.random.default_rng(0)
        embeddings = [rng.standard_normal(build_index.EMBEDDING_DIM).tolist() for _ in range(5)]
        index = build_index.build_faiss_index(embeddings)
        assert index.ntotal == 5
        query = np.array([embeddings[3]], dtype="float32")
        import faiss

        faiss.normalize_L2(query)
        _, ids = index.search(query, 1)
        assert ids[0][0] == 3


class FakeEmbeddings:
    """Deterministic stand-in for client.embeddings: one vector per text,
    derived from its hash; records every text it was asked to embed."""

    def __init__(self):
        self.calls: list[str] = []

    def create(self, model, input):
        import numpy as np
        from types import SimpleNamespace

        self.calls.extend(input)
        data = []
        for text in input:
            seed = int(build_index.content_key(text)[:8], 16)
            vector = np.random.default_rng(seed).standard_normal(build_index.EMBEDDING_DIM)
            data.append(SimpleNamespace(embedding=vector.tolist()))
        return SimpleNamespace(data=data)


class TestIncrementalBuild:
    @pytest.fixture
    def env(self, tmp_path, monkeypatch):
        from types import SimpleNamespace

        source = tmp_path / "src.jsonl"
        monkeypatch.setattr(build_index, "INPUT_FILES", [(source, "src")])
        monkeypatch.setattr(build_index, "MERGED_OUTPUT_PATH", tmp_path / "merged.jsonl")
        db_path = tmp_path / "metadata.db"
        index_path = tmp_path / "faiss_index.bin"
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
        monkeypatch.setenv("FAISS_INDEX_PATH", str(index_path))
        monkeypatch.setenv("OPENAI_API_KEY", "test")
        embeddings = FakeEmbeddings()
        monkeypatch.setattr(build_index, "OpenAI", lambda api_key: SimpleNamespace(embeddings=embeddings))

        def write(*contents):
            source.write_text("".join(
                json.dumps({"url": f"u{i}", "title": "t", "topic": "x", "content": c, "crawled_at": "d"}) + "\n"
                for i, c in enumerate(contents)
            ))

        def build(*argv):
            monkeypatch.setattr("sys.argv", ["build_index.py", *argv])
            embeddings.calls.clear()
            build_index.main()
            return list(embeddings.calls)

        return SimpleNamespace(write=write, build=build, index_path=index_path, db=f"sqlite:///{db_path}")

    def test_first_build_embeds_everything(self, env):
        env.write("alpha", "beta")
        assert sorted(env.build()) == ["alpha", "beta"]

    def test_unchanged_input_writes_nothing(self, env, capsys):
        env.write("alpha", "beta")
        env.build()
        mtime = env.index_path.stat().st_mtime_ns
        assert env.build() == []
        assert env.index_path.stat().st_mtime_ns == mtime
        assert "unchanged" in capsys.readouterr().out

    def test_only_new_or_changed_chunks_are_embedded(self, env):
        env.write("alpha", "beta")
        env.build()
        env.write("alpha", "beta changed", "gamma")
        assert sorted(env.build()) == ["beta changed", "gamma"]

    def test_reused_vectors_land_on_the_right_ids(self, env):
        import faiss
        import numpy as np

        env.write("alpha", "beta")
        env.build()
        env.write("gamma", "beta", "alpha")  # reorder: ids shift
        env.build()
        rows, vectors = build_index.load_previous_build(env.db, env.index_path)
        assert [r[4] for r in rows] == ["gamma", "beta", "alpha"]
        index = faiss.read_index(str(env.index_path))
        for i, text in enumerate(["gamma", "beta", "alpha"]):
            expected = np.array([FakeEmbeddings().create(None, [text]).data[0].embedding], dtype="float32")
            faiss.normalize_L2(expected)
            _, ids = index.search(expected, 1)
            assert ids[0][0] == i

    def test_full_flag_re_embeds_everything(self, env):
        env.write("alpha", "beta")
        env.build()
        assert sorted(env.build("--full")) == ["alpha", "beta"]

    def test_no_previous_build_returns_empty(self, env):
        assert build_index.load_previous_build(env.db, env.index_path) == ([], {})
