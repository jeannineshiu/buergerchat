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
