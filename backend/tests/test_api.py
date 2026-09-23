"""Integration tests: the FastAPI app end-to-end through TestClient, with
the two external dependencies stubbed: RAGPipeline.answer() records the
plan it gets, and turn planning runs for real against a fake PVOG finder
and translation. Routing itself is covered in test_turn_plan.py; this file
covers the HTTP layer — validation, rate limiting, the answer cache, the
daily budget, feedback persistence and error mapping."""

import pytest
from fastapi.testclient import TestClient

import main
from behoerde import BehoerdeResult
from rag import IndexNotReadyError
from turn_plan import Found, Kind, TurnPlanner


@pytest.fixture()
def client(monkeypatch):
    main.limiter.enabled = False
    # Module-level cache: without this, a question asked in one test would
    # be answered from the cache in the next and never reach fake_answer.
    main.answer_cache.clear()

    calls = {"answer_count": 0}

    def fake_answer(plan):
        calls["answer_count"] += 1
        calls["plan"] = plan
        if plan.kind is not Kind.ANSWER:
            return "STUB ANSWER", []
        sources = [{"title": "Doc", "url": "https://example.org"}]
        if isinstance(plan.authority, Found):
            sources.insert(0, plan.authority.result.source())
        return "STUB ANSWER", sources

    class FakeFinder:
        def find(self, plz, query, topic=None):
            return BehoerdeResult(authority_name="Jobcenter Test", service_name="X",
                                  website="https://jc.example")

    monkeypatch.setattr(main.rag_pipeline, "answer", fake_answer)
    monkeypatch.setattr(
        main, "turn_planner",
        TurnPlanner(main.query_router, FakeFinder(), lambda text, language: text),
    )
    test_client = TestClient(main.app)
    test_client.calls = calls
    return test_client


class TestChat:
    def test_basic_question(self, client):
        r = client.post("/chat", json={"message": "Was ist Bürgergeld?"})
        assert r.status_code == 200
        assert r.json() == {
            "answer": "STUB ANSWER",
            "topic": "buergergeld",
            "sources": [{"title": "Doc", "url": "https://example.org"}],
        }

    def test_request_reaches_the_plan(self, client):
        history = [
            {"role": "user", "content": "Wo beantrage ich Kindergeld?"},
            {"role": "assistant", "content": "Bitte nennen Sie Ihre Postleitzahl."},
        ]
        r = client.post("/chat", json={"message": "10115", "language": "zh-Hant", "history": history})
        plan = client.calls["plan"]
        assert (plan.message, plan.language, plan.history) == ("10115", "zh-Hant", tuple(history))
        assert r.json()["topic"] == "kindergeld"  # response topic is the plan's
        assert r.json()["sources"][0]["title"] == "Jobcenter Test — X"

    def test_meta_question_has_no_sources(self, client):
        r = client.post("/chat", json={"message": "Welche Fragen kann ich dir stellen?"})
        assert r.status_code == 200
        assert r.json()["sources"] == []
        assert r.json()["topic"] == "allgemein"

    def test_index_not_ready_maps_to_503(self, client, monkeypatch):
        def raising_answer(plan):
            raise IndexNotReadyError("missing")

        monkeypatch.setattr(main.rag_pipeline, "answer", raising_answer)
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

    def test_minute_limit_says_rate_limit(self, client):
        main.limiter.enabled = True
        try:
            for _ in range(10):
                client.post("/chat", json={"message": "Hallo"},
                            headers={"X-Forwarded-For": "203.0.113.10"})
            r = client.post("/chat", json={"message": "Hallo"},
                            headers={"X-Forwarded-For": "203.0.113.10"})
        finally:
            main.limiter.enabled = False
        assert r.status_code == 429
        assert r.json()["code"] == "rate_limit"

    def test_daily_limit_says_come_back_tomorrow(self, client, monkeypatch):
        # Step a fake clock past each minute window so only the daily
        # counter (CHAT_DAILY_LIMIT=30 in conftest) can trip.
        import limits.storage.memory as memory

        now = [memory.time.time()]
        monkeypatch.setattr(memory.time, "time", lambda: now[0])
        main.limiter.enabled = True
        try:
            statuses = []
            for _ in range(3):
                for _ in range(10):
                    statuses.append(client.post(
                        "/chat", json={"message": "Hallo"},
                        headers={"X-Forwarded-For": "203.0.113.11"}).status_code)
                now[0] += 61
            r = client.post("/chat", json={"message": "Hallo"},
                            headers={"X-Forwarded-For": "203.0.113.11"})
        finally:
            main.limiter.enabled = False
        assert statuses == [200] * 30
        assert r.status_code == 429
        assert r.json()["code"] == "daily_limit"


class TestAnswerCache:
    def test_repeated_first_question_is_answered_from_cache(self, client):
        first = client.post("/chat", json={"message": "Was ist Bürgergeld?"})
        second = client.post("/chat", json={"message": " Was ist  Bürgergeld? "})
        assert second.json() == first.json()
        assert client.calls["answer_count"] == 1

    def test_language_is_part_of_the_key(self, client):
        client.post("/chat", json={"message": "Was ist Bürgergeld?", "language": "de"})
        client.post("/chat", json={"message": "Was ist Bürgergeld?", "language": "en"})
        assert client.calls["answer_count"] == 2

    def test_turns_with_history_are_never_cached(self, client):
        history = [
            {"role": "user", "content": "Wer bekommt Kindergeld?"},
            {"role": "assistant", "content": "Eltern …"},
        ]
        for _ in range(2):
            client.post("/chat", json={"message": "Und wie viel?", "history": history})
        assert client.calls["answer_count"] == 2

    def test_no_cache_header_reaches_the_pipeline(self, client):
        client.post("/chat", json={"message": "Was ist Bürgergeld?"})
        client.post("/chat", json={"message": "Was ist Bürgergeld?"},
                    headers={"Cache-Control": "no-cache"})
        assert client.calls["answer_count"] == 2

    def test_errors_are_not_cached(self, client, monkeypatch):
        def raising_answer(plan):
            raise IndexNotReadyError("missing")

        original = main.rag_pipeline.answer
        monkeypatch.setattr(main.rag_pipeline, "answer", raising_answer)
        assert client.post("/chat", json={"message": "Was ist Bürgergeld?"}).status_code == 503
        monkeypatch.setattr(main.rag_pipeline, "answer", original)
        assert client.post("/chat", json={"message": "Was ist Bürgergeld?"}).status_code == 200


class TestDailyBudget:
    def test_exhausted_budget_returns_503_with_code(self, client, monkeypatch):
        monkeypatch.setattr(main.daily_budget, "exhausted", lambda: True)
        r = client.post("/chat", json={"message": "Was ist Bürgergeld?"})
        assert r.status_code == 503
        assert r.json()["code"] == "daily_budget_exhausted"
        assert client.calls["answer_count"] == 0

    def test_cached_answers_still_served_when_exhausted(self, client, monkeypatch):
        client.post("/chat", json={"message": "Was ist Bürgergeld?"})
        monkeypatch.setattr(main.daily_budget, "exhausted", lambda: True)
        r = client.post("/chat", json={"message": "Was ist Bürgergeld?"})
        assert r.status_code == 200
        assert client.calls["answer_count"] == 1


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

    def test_model_check_reports_every_model(self, client, monkeypatch):
        monkeypatch.setattr(
            main.rag_pipeline, "check_models", lambda: {"gpt-5.5": "ok", "emb": "ok"}
        )
        r = client.get("/health/model")
        assert r.status_code == 200
        assert r.json() == {"status": "ok", "models": {"gpt-5.5": "ok", "emb": "ok"}}

    def test_model_check_503_when_a_model_is_gone(self, client, monkeypatch):
        # The 2026-09-09 shape: the model is deprecated, so every call 404s
        # while /health still reports the index is loaded.
        def gone():
            raise RuntimeError("model_not_found: gpt-5.3-chat-latest")

        monkeypatch.setattr(main.rag_pipeline, "check_models", gone)
        r = client.get("/health/model")
        assert r.status_code == 503
        assert r.json()["status"] == "error"
        assert "model_not_found" in r.json()["detail"]
