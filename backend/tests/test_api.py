"""Integration tests: the FastAPI app end-to-end through TestClient, with
the two external dependencies (RAG pipeline / PVOG finder) stubbed at the
module boundary. Covers routing logic, validation, rate limiting, the
feedback persistence path and error mapping."""

import pytest
from fastapi.testclient import TestClient

import main
from behoerde import BehoerdeResult
from rag import IndexNotReadyError


@pytest.fixture()
def client(monkeypatch):
    main.limiter.enabled = False

    calls = {}

    def fake_query(message, language="de", topic=None, authority=None,
                   ask_for_plz=False, authority_missing=False, history=None,
                   meta_only=False, chitchat=False, retrieval_query=None):
        calls["query"] = {
            "message": message, "language": language, "topic": topic,
            "authority": authority, "ask_for_plz": ask_for_plz,
            "authority_missing": authority_missing, "meta_only": meta_only,
            "chitchat": chitchat, "retrieval_query": retrieval_query,
        }
        sources = [{"title": "Doc", "url": "https://example.org"}]
        if authority is not None:
            sources.insert(0, authority.source())
        return "STUB ANSWER", sources

    def fake_find(plz, query, topic=None):
        calls["find"] = {"plz": plz, "query": query, "topic": topic}
        if plz == "99999":
            return None
        return BehoerdeResult(authority_name="Jobcenter Test", service_name="X",
                              website="https://jc.example")

    monkeypatch.setattr(main.rag_pipeline, "query", fake_query)
    monkeypatch.setattr(main.behoerde_finder, "find", fake_find)
    test_client = TestClient(main.app)
    test_client.calls = calls
    return test_client


class TestChat:
    def test_basic_question(self, client):
        r = client.post("/chat", json={"message": "Was ist Bürgergeld?"})
        assert r.status_code == 200
        body = r.json()
        assert body["answer"] == "STUB ANSWER"
        assert body["topic"] == "buergergeld"
        assert body["sources"] == [{"title": "Doc", "url": "https://example.org"}]
        assert "find" not in client.calls  # no authority intent → no PVOG call

    def test_authority_intent_with_plz_calls_finder(self, client):
        r = client.post("/chat", json={"message": "Wo ist mein Jobcenter? Ich wohne in 81667"})
        assert r.status_code == 200
        assert client.calls["find"]["plz"] == "81667"
        assert r.json()["sources"][0]["title"] == "Jobcenter Test — X"

    def test_authority_intent_without_plz_asks_for_it(self, client):
        client.post("/chat", json={"message": "Wo beantrage ich Kindergeld?"})
        assert client.calls["query"]["ask_for_plz"] is True
        assert "find" not in client.calls

    def test_bare_plz_followup_uses_history(self, client):
        history = [
            {"role": "user", "content": "Wo beantrage ich Kindergeld?"},
            {"role": "assistant", "content": "Bitte nennen Sie Ihre Postleitzahl."},
        ]
        r = client.post("/chat", json={"message": "10115", "history": history})
        assert r.status_code == 200
        assert client.calls["find"]["plz"] == "10115"
        # topic and lookup text come from the history, not the bare PLZ
        assert client.calls["find"]["topic"] == "kindergeld"
        assert client.calls["find"]["query"] == "Wo beantrage ich Kindergeld?"

    def test_short_followup_enriches_retrieval_with_history(self, client):
        # "say that in Chinese" carries no searchable meaning — retrieval
        # must reuse the previous question (the reported bug: random chunks).
        history = [
            {"role": "user", "content": "Wer bekommt Kindergeld?"},
            {"role": "assistant", "content": "Kindergeld bekommen Eltern …"},
        ]
        client.post("/chat", json={"message": "用中文講一次", "history": history})
        q = client.calls["query"]
        assert q["retrieval_query"] == "Wer bekommt Kindergeld?\n用中文講一次"
        assert q["message"] == "用中文講一次"  # prompt still shows the real message

    def test_fresh_topical_question_keeps_plain_retrieval(self, client):
        client.post("/chat", json={"message": "Was ist Bürgergeld?"})
        assert client.calls["query"]["retrieval_query"] is None

    def test_failed_lookup_sets_authority_missing(self, client):
        client.post("/chat", json={"message": "Wo ist mein Jobcenter? PLZ 99999"})
        assert client.calls["query"]["authority_missing"] is True

    def test_meta_question_skips_retrieval_and_has_no_sources(self, client):
        r = client.post("/chat", json={"message": "Welche Fragen kann ich dir stellen?"})
        assert r.status_code == 200
        assert r.json()["sources"] == []
        assert client.calls["query"]["meta_only"] is True

    def test_chitchat_skips_retrieval_and_has_no_sources(self, client):
        r = client.post("/chat", json={"message": "Danke!"})
        assert r.status_code == 200
        assert r.json()["sources"] == []
        assert client.calls["query"]["chitchat"] is True

    def test_question_starting_with_greeting_is_not_chitchat(self, client):
        client.post("/chat", json={"message": "Hi, wo ist mein Jobcenter?"})
        assert client.calls["query"]["chitchat"] is False

    def test_index_not_ready_maps_to_503(self, client, monkeypatch):
        def raising_query(*args, **kwargs):
            raise IndexNotReadyError("missing")

        monkeypatch.setattr(main.rag_pipeline, "query", raising_query)
        r = client.post("/chat", json={"message": "Was ist Bürgergeld?"})
        assert r.status_code == 503
        assert r.json() == {"error": "Index not yet available. Please try again later."}


class TestValidation:
    def test_empty_message_rejected(self, client):
        assert client.post("/chat", json={"message": ""}).status_code == 422

    def test_oversize_message_rejected(self, client):
        assert client.post("/chat", json={"message": "x" * 2001}).status_code == 422

    def test_oversize_history_rejected(self, client):
        history = [{"role": "user", "content": "x"}] * 21
        assert client.post("/chat", json={"message": "hi", "history": history}).status_code == 422

    def test_invalid_history_role_rejected(self, client):
        history = [{"role": "system", "content": "x"}]
        assert client.post("/chat", json={"message": "hi", "history": history}).status_code == 422


class TestRateLimit:
    def test_chat_returns_429_after_limit(self, client):
        main.limiter.enabled = True
        try:
            statuses = [
                client.post(
                    "/chat",
                    json={"message": "Hallo Welt"},
                    headers={"X-Forwarded-For": "203.0.113.7"},
                ).status_code
                for _ in range(11)
            ]
        finally:
            main.limiter.enabled = False
        assert statuses[:10] == [200] * 10
        assert statuses[10] == 429

    def test_limit_is_per_ip(self, client):
        main.limiter.enabled = True
        try:
            for _ in range(10):
                client.post("/chat", json={"message": "Hallo"},
                            headers={"X-Forwarded-For": "203.0.113.8"})
            other = client.post("/chat", json={"message": "Hallo"},
                                headers={"X-Forwarded-For": "203.0.113.9"})
        finally:
            main.limiter.enabled = False
        assert other.status_code == 200


class TestFeedback:
    def test_message_feedback_persists(self, client):
        r = client.post("/feedback/message", json={
            "message_id": "m-test-1", "session_id": "s-test-1",
            "rating": "down", "comment": "zu lang", "topic": "kindergeld",
        })
        assert r.status_code == 201

        from app.db import FeedbackSessionLocal
        from app.models import FeedbackMessage

        session = FeedbackSessionLocal()
        row = session.query(FeedbackMessage).filter_by(message_id="m-test-1").one()
        session.close()
        assert row.rating == "down" and row.comment == "zu lang"

    def test_session_feedback_persists(self, client):
        r = client.post("/feedback/session", json={"session_id": "s-test-2", "rating": 4})
        assert r.status_code == 201

        from app.db import FeedbackSessionLocal
        from app.models import FeedbackSession

        session = FeedbackSessionLocal()
        row = session.query(FeedbackSession).filter_by(session_id="s-test-2").one()
        session.close()
        assert row.rating == 4

    def test_invalid_ratings_rejected(self, client):
        assert client.post("/feedback/session", json={"session_id": "s", "rating": 6}).status_code == 422
        assert client.post("/feedback/message", json={
            "message_id": "m", "session_id": "s", "rating": "meh",
        }).status_code == 422


class TestHealth:
    def test_health_degraded_when_index_missing(self, client, monkeypatch):
        monkeypatch.setattr(main.rag_pipeline, "load", lambda: False)
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "degraded", "index": "missing"}

    def test_health_ok_when_index_loaded(self, client, monkeypatch):
        monkeypatch.setattr(main.rag_pipeline, "load", lambda: True)
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok", "index": "loaded"}
