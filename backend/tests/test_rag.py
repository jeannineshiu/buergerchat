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

# Two chunks of the same long page: retrieval may return both, the visible
# source list must name the page once.
SAME_PAGE_CHUNKS = [
    (3, "Kindergeld Teil eins: Anspruch und Höhe der Leistung."),
    (4, "Kindergeld Teil zwei: Antrag und Auszahlung der Leistung."),
]

# Same article syndicated under a different per-Ort URL (arbeitsagentur.de
# pattern) — identical title, distinct URL, must also be deduped. The second
# copy differs only by whitespace in the title (real data has both variants).
SYNDICATED_CHUNK = (5, "Kindergeld Teil eins: Anspruch und Höhe im Überblick.")
SYNDICATED_WHITESPACE_CHUNK = (6, "Kindergeld Teil eins: Anspruch und Höhe genauer.")


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
    for cid, text in SAME_PAGE_CHUNKS:
        session.add(Chunk(id=cid, url="https://example.org/kindergeld", title="Kindergeld", content=text))
    session.add(Chunk(id=SYNDICATED_CHUNK[0], url="https://example.org/vor-ort/x/kindergeld",
                      title="Kindergeld", content=SYNDICATED_CHUNK[1]))
    session.add(Chunk(id=SYNDICATED_WHITESPACE_CHUNK[0], url="https://example.org/vor-ort/y/kindergeld",
                      title="Kindergeld ", content=SYNDICATED_WHITESPACE_CHUNK[1]))
    session.commit()
    session.close()

    # Build the FAISS index from the same fake embeddings the query will use.
    all_chunks = CHUNKS + SAME_PAGE_CHUNKS + [SYNDICATED_CHUNK, SYNDICATED_WHITESPACE_CHUNK]
    vectors = np.array(
        [fake_openai.embeddings.create(model="x", input=text).data[0].embedding for _, text in all_chunks],
        dtype="float32",
    )
    faiss.normalize_L2(vectors)
    index = faiss.IndexIDMap(faiss.IndexFlatIP(1536))
    index.add_with_ids(vectors, np.array([cid for cid, _ in all_chunks], dtype="int64"))
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


class TestQueryTranslation:
    def _capture_embed_inputs(self, pipeline):
        captured = []
        original = pipeline.client.embeddings.create

        def recording_create(model, input):  # noqa: A002 - OpenAI SDK signature
            captured.append(input)
            return original(model=model, input=input)

        pipeline.client.embeddings.create = recording_create
        return captured

    def test_non_latin_query_is_translated_before_embedding(self, pipeline):
        captured = self._capture_embed_inputs(pipeline)
        pipeline.retrieve("Kindergeld 可以補領嗎？")
        # The fake chat client answers "STUB ANSWER" — that translation,
        # not the original Chinese, must be what gets embedded.
        assert captured == ["STUB ANSWER"]
        # The translation is the first chat call; the rerank follows it.
        system = pipeline.client.chat.completions.calls[0][0]
        assert "Übersetze" in system["content"]

    def test_latin_query_embeds_directly_without_translation_call(self, pipeline):
        captured = self._capture_embed_inputs(pipeline)
        pipeline.retrieve("Wie hoch ist das Kindergeld?")
        assert captured == ["Wie hoch ist das Kindergeld?"]
        prompts = [call[0]["content"] for call in pipeline.client.chat.completions.calls]
        assert not any("Übersetze" in prompt for prompt in prompts)

    def test_latin_non_german_language_is_translated(self, pipeline):
        # Turkish/Polish/etc. queries are Latin-script but embed poorly
        # against the German corpus — the request language triggers the
        # translation even without a script signal.
        captured = self._capture_embed_inputs(pipeline)
        pipeline.retrieve("Kaç yaşında emekli olabilirim?", language="tr")
        assert captured == ["STUB ANSWER"]

    def test_translation_failure_falls_back_to_original(self, pipeline):
        captured = self._capture_embed_inputs(pipeline)

        def broken_create(model, messages, **kwargs):
            raise RuntimeError("api down")

        pipeline.client.chat.completions.create = broken_create
        chunks = pipeline.retrieve("Kindergeld 可以補領嗎？")
        assert captured == ["Kindergeld 可以補領嗎？"]
        assert isinstance(chunks, list)


class TestQuery:
    def test_retrieves_matching_chunk_as_source(self, pipeline):
        answer, sources = pipeline.query("Bürgergeld ist eine Leistung des Jobcenters.")
        assert answer == "STUB ANSWER"
        assert sources[0]["url"] == "https://example.org/0"

    def test_sources_deduped_by_url(self, pipeline, monkeypatch):
        monkeypatch.setattr(rag, "TOP_K", 7)  # retrieve everything → all dupes present
        # Both halves of the Kindergeld page should be retrieved (identical
        # first words → similar fake embeddings), but the source appears once.
        _, sources = pipeline.query("Kindergeld Teil eins: Anspruch und Höhe der Leistung.")
        urls = [s["url"] for s in sources]
        norm_titles = [" ".join(s["title"].split()).lower() for s in sources]
        assert len(urls) == len(set(urls))
        assert len(norm_titles) == len(set(norm_titles))  # incl. whitespace variants
        assert "https://example.org/kindergeld" in urls

    def test_authority_not_duplicated_when_also_retrieved(self, pipeline):
        authority = BehoerdeResult(
            authority_name="Familienkasse", service_name="Kindergeld",
            website="https://example.org/0",  # same URL as a retrieved chunk
        )
        _, sources = pipeline.query(
            "Bürgergeld ist eine Leistung des Jobcenters.", authority=authority
        )
        urls = [s["url"] for s in sources]
        assert urls.count("https://example.org/0") == 1
        assert sources[0]["title"] == "Familienkasse — Kindergeld"

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

    def test_chitchat_skips_retrieval_and_sources(self, pipeline):
        answer, sources = pipeline.query("Hallo", chitchat=True)
        assert answer == "STUB ANSWER"
        assert sources == []
        prompt = pipeline.client.chat.completions.last_messages[-1]["content"]
        assert "Small Talk" in prompt

    def test_ask_for_topic_skips_retrieval_and_sources(self, pipeline):
        # "Which office is responsible?" with no subject is answered with a
        # question back — citing whatever the embedding happened to match
        # (Baugenehmigung, Gewerbe anmelden) only looks like evidence.
        answer, sources = pipeline.query("Which office is responsible?", ask_for_topic=True)
        assert answer == "STUB ANSWER"
        assert sources == []
        prompt = pipeline.client.chat.completions.last_messages[-1]["content"]
        assert "worum es geht" in prompt

    def test_history_is_passed_and_truncated(self, pipeline):
        history = [{"role": "user", "content": f"msg{i}"} for i in range(10)]
        pipeline.query("Bürgergeld", history=history)
        messages = pipeline.client.chat.completions.last_messages
        history_contents = [m["content"] for m in messages if m["content"].startswith("msg")]
        assert history_contents == [f"msg{i}" for i in range(4, 10)]  # last 6

    def test_third_language_leak_triggers_corrective_retry(self, pipeline):
        # Call sequence for language=zh-Hant (reranking is off by default):
        # query translation (Übersetze), first answer (leaks Thai), retry.
        answers = iter(["Kindergeld rückwirkend", "最多可ย้อนหลัง領 6 個月", "最多可追溯領 6 個月"])
        calls = []

        def fake_create(model, messages, **kwargs):
            calls.append(messages)
            message = type("Msg", (), {"content": next(answers)})()
            choice = type("Choice", (), {"message": message})()
            return type("Completion", (), {"choices": [choice]})()

        pipeline.client.chat.completions.create = fake_create
        answer, _ = pipeline.query("Kindergeld rückwirkend", language="zh-Hant")
        assert answer == "最多可追溯領 6 個月"
        assert len(calls) == 3
        assert "Übersetze" in calls[0][0]["content"]
        assert "mixes in another language" in calls[2][-1]["content"]

    def test_clean_answer_needs_no_retry(self, pipeline):
        answer, _ = pipeline.query("Bürgergeld", language="zh-Hant")
        assert answer == "STUB ANSWER"

    def test_digits_directive_in_every_answer_prompt(self, pipeline):
        for language in ("de", "zh-Hant"):
            pipeline.query("Wie hoch ist das Kindergeld?", language=language)
            prompt = pipeline.client.chat.completions.last_messages[-1]["content"]
            assert "Write every number as digits" in prompt

    def test_ask_for_plz_directive_in_prompt(self, pipeline):
        pipeline.query("Wo ist mein Jobcenter?", ask_for_plz=True)
        prompt = pipeline.client.chat.completions.last_messages[-1]["content"]
        assert "Postleitzahl" in prompt

    def test_authority_missing_directive_forbids_invention(self, pipeline):
        pipeline.query("Wo ist mein Jobcenter?", authority_missing=True)
        prompt = pipeline.client.chat.completions.last_messages[-1]["content"]
        assert "ERFINDE KEINE" in prompt


class TestReasoningEffort:
    """gpt-5.5's default reasoning made /chat take 21-27 s; each call now
    sends an explicit effort, split into helper calls and the answer."""

    def _efforts(self, pipeline):
        fake = pipeline.client.chat.completions
        return [
            (call[0]["content"][:12], kwargs.get("reasoning_effort", "<unset>"))
            for call, kwargs in zip(fake.calls, fake.call_kwargs)
        ]

    def test_helper_and_answer_efforts_are_sent_separately(self, pipeline, monkeypatch):
        monkeypatch.setattr(rag, "RERANK", True)
        monkeypatch.setattr(rag, "HELPER_REASONING_EFFORT", "none")
        monkeypatch.setattr(rag, "ANSWER_REASONING_EFFORT", "low")
        pipeline.query("Kindergeld 可以補領嗎？", language="zh-Hant")
        efforts = self._efforts(pipeline)
        # translation, rerank, answer — in that order
        assert [e for _, e in efforts] == ["none", "none", "low"]
        assert efforts[0][0].startswith("Übersetze")
        assert efforts[1][0].startswith("Du bewertest")

    def test_empty_effort_sends_no_parameter(self, pipeline, monkeypatch):
        # For a CHAT_MODEL override that doesn't accept reasoning_effort.
        monkeypatch.setattr(rag, "HELPER_REASONING_EFFORT", "")
        monkeypatch.setattr(rag, "ANSWER_REASONING_EFFORT", "")
        pipeline.query("Kindergeld 可以補領嗎？", language="zh-Hant")
        assert all(
            "reasoning_effort" not in kwargs
            for kwargs in pipeline.client.chat.completions.call_kwargs
        )

    def test_corrective_retry_uses_the_answer_effort(self, pipeline, monkeypatch):
        monkeypatch.setattr(rag, "ANSWER_REASONING_EFFORT", "medium")
        fake = pipeline.client.chat.completions
        replies = iter(["補發 ย้อนหลัง", "補發"])
        original = fake.create

        def leaky_then_clean(model, messages, **kwargs):
            completion = original(model=model, messages=messages, **kwargs)
            completion.choices[0].message.content = next(replies)
            return completion

        fake.create = leaky_then_clean
        # German: no translation call, so the only calls are answer + retry.
        pipeline.query("Wie hoch ist das Kindergeld?", language="de")
        assert [k.get("reasoning_effort") for k in fake.call_kwargs] == ["medium", "medium"]


class TestUsageReporting:
    def test_every_openai_response_is_reported(self, pipeline, monkeypatch):
        monkeypatch.setattr(rag, "RERANK", True)
        reported = []
        pipeline._on_usage = lambda model, usage: reported.append(model)
        pipeline.query("Kindergeld 可以補領嗎？", language="zh-Hant")
        # translation, embedding, rerank, answer
        assert reported == [rag.CHAT_MODEL, rag.EMBEDDING_MODEL, rag.RERANK_MODEL, rag.CHAT_MODEL]

    def test_no_callback_is_fine(self, pipeline):
        pipeline._on_usage = None
        answer, _ = pipeline.query("Wie hoch ist das Kindergeld?")
        assert answer == "STUB ANSWER"


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


class TestRerank:
    """Vector similarity cannot separate the answer from same-topic noise on
    amount questions (the chunk stating the Regelsatz sat at rank 21 of 30),
    so retrieve() searches wide and appends model-picked extras after the
    untouched vector top-K — augmenting, never evicting, a vector hit."""

    @pytest.fixture(autouse=True)
    def widen(self, pipeline, monkeypatch):
        # The shared fixture pins TOP_K at 2; with the 7-chunk fixture index,
        # TOP_K=3 leaves 4 candidates outside the head for extras to come
        # from. Depends on `pipeline` so this runs after it, not before.
        monkeypatch.setattr(rag, "TOP_K", 3)
        # Reranking ships disabled — these tests cover the code path behind
        # the flag, so they have to switch it on.
        monkeypatch.setattr(rag, "RERANK", True)

    def _pick(self, pipeline, reply):
        """Force the reranker's answer and return the retrieved chunk ids."""

        def fake_create(model, messages, **kwargs):
            message = type("Msg", (), {"content": reply})()
            return type("Completion", (), {"choices": [type("Choice", (), {"message": message})()]})()

        pipeline.client.chat.completions.create = fake_create
        return [chunk.id for chunk in pipeline.retrieve("Wie hoch ist das Kindergeld?")]

    def test_reranker_sees_all_candidates(self, pipeline):
        seen = []
        original = pipeline._rerank
        pipeline._rerank = lambda query, candidates: (seen.append(len(candidates)), original(query, candidates))[1]
        chunks = pipeline.retrieve("Wie hoch ist das Kindergeld?")
        # The fixture index holds 7 chunks and CANDIDATE_K is far wider, so
        # every chunk becomes a candidate.
        assert seen == [7]
        assert len(chunks) <= rag.TOP_K + rag.RERANK_EXTRA_K

    def test_vector_head_is_never_evicted(self, pipeline):
        vector_order = self._pick(pipeline, "")  # unparseable -> no extras
        picked = self._pick(pipeline, "7,6,5")
        assert picked[: rag.TOP_K] == vector_order

    def test_picks_outside_the_head_are_appended_in_model_order(self, pipeline):
        vector_order = self._pick(pipeline, "")
        # A single-number reply appends exactly that candidate — which is how
        # these lookups learn the id behind a candidate number.
        seventh = self._pick(pipeline, "7")[-1]
        fifth = self._pick(pipeline, "5")[-1]
        picked = self._pick(pipeline, "7,5")
        assert picked == vector_order + [seventh, fifth]

    def test_picks_already_in_the_head_add_nothing(self, pipeline):
        vector_order = self._pick(pipeline, "")
        assert self._pick(pipeline, "1,2,3") == vector_order

    def test_extras_are_capped_at_rerank_extra_k(self, pipeline, monkeypatch):
        monkeypatch.setattr(rag, "RERANK_EXTRA_K", 1)
        picked = self._pick(pipeline, "7,6,5,4")
        assert len(picked) == rag.TOP_K + 1

    def test_out_of_range_and_duplicate_numbers_are_ignored(self, pipeline):
        vector_order = self._pick(pipeline, "")
        seventh = self._pick(pipeline, "7")[-1]
        picked = self._pick(pipeline, "999,7,7,0")
        assert picked == vector_order + [seventh]

    def test_api_failure_falls_back_to_vector_order(self, pipeline):
        def boom(model, messages, **kwargs):
            raise RuntimeError("rerank is down")

        vector_order = self._pick(pipeline, "")
        pipeline.client.chat.completions.create = boom
        assert [c.id for c in pipeline.retrieve("Wie hoch ist das Kindergeld?")] == vector_order

    def test_disabling_rerank_skips_the_extra_call(self, pipeline, monkeypatch):
        monkeypatch.setattr(rag, "RERANK", False)
        pipeline.client.chat.completions.calls.clear()
        chunks = pipeline.retrieve("Wie hoch ist das Kindergeld?")
        assert len(chunks) <= rag.TOP_K
        assert pipeline.client.chat.completions.calls == []
