"""Daily OpenAI spend cap (budget.py) and the first-turn answer cache."""

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine

from answer_cache import AnswerCache, cache_key
from budget import FALLBACK_PRICE, DailyBudget, cost_usd, parse_limit, price_for


def usage(prompt=0, completion=0, cached=0):
    return SimpleNamespace(
        prompt_tokens=prompt,
        completion_tokens=completion,
        prompt_tokens_details=SimpleNamespace(cached_tokens=cached),
    )


@pytest.fixture()
def budget(tmp_path):
    day = ["2026-09-10"]
    engine = create_engine(f"sqlite:///{tmp_path}/usage.db")
    b = DailyBudget(engine, limit_usd=0.50, today=lambda: day[0])
    b.day = day
    return b


class TestCost:
    def test_gpt55_input_and_output(self):
        # 1M in at $5 + 1M out at $30
        assert cost_usd("gpt-5.5", usage(1_000_000, 1_000_000)) == pytest.approx(35.0)

    def test_cached_input_is_cheaper(self):
        # 1M prompt tokens, all cached: $0.50 instead of $5
        assert cost_usd("gpt-5.5", usage(1_000_000, 0, cached=1_000_000)) == pytest.approx(0.50)

    def test_typical_answer_call(self):
        # ~2.6k in, ~450 out at reasoning none: about half a cent + 1.35 ct
        assert cost_usd("gpt-5.5", usage(2600, 450)) == pytest.approx(0.0265)

    def test_embedding_usage_has_no_completion(self):
        embedding_usage = SimpleNamespace(prompt_tokens=1_000_000, total_tokens=1_000_000)
        assert cost_usd("text-embedding-3-small", embedding_usage) == pytest.approx(0.02)

    def test_dated_snapshot_uses_base_price_and_longest_prefix_wins(self):
        assert price_for("gpt-5.5-2026-08-01") == price_for("gpt-5.5")
        assert price_for("gpt-5.4-mini") != price_for("gpt-5.4-nano")

    def test_unknown_model_is_costed_as_the_most_expensive(self):
        assert price_for("some-new-model") == FALLBACK_PRICE

    def test_missing_usage_costs_nothing(self):
        assert cost_usd("gpt-5.5", None) == 0.0


class TestParseLimit:
    def test_default_is_fifty_cents(self):
        assert parse_limit(None) == 0.50
        assert parse_limit("") == 0.50

    def test_explicit_amount(self):
        assert parse_limit("2") == 2.0

    def test_off_disables(self):
        assert parse_limit("off") is None


class TestDailyBudget:
    def test_spend_accumulates_until_the_cap(self, budget):
        assert not budget.exhausted()
        budget.record("gpt-5.5", usage(40_000, 5_000))  # $0.20 + $0.15
        assert budget.spent_today() == pytest.approx(0.35)
        assert not budget.exhausted()
        budget.record("gpt-5.5", usage(30_000, 0))  # +$0.15 → exactly the cap
        assert budget.exhausted()

    def test_a_new_day_starts_from_zero(self, budget):
        budget.record("gpt-5.5", usage(200_000, 0))  # $1.00
        assert budget.exhausted()
        budget.day[0] = "2026-09-11"
        assert budget.spent_today() == 0.0
        assert not budget.exhausted()

    def test_disabled_cap_is_never_exhausted(self, tmp_path):
        b = DailyBudget(create_engine(f"sqlite:///{tmp_path}/u.db"), limit_usd=None)
        b.record("gpt-5.5", usage(10_000_000, 0))
        assert not b.exhausted()

    def test_recording_never_raises(self, budget, capsys):
        budget.engine.dispose()
        budget.engine = create_engine("sqlite:////nonexistent-dir/usage.db")
        budget.record("gpt-5.5", usage(1000, 1000))  # must not raise
        assert "could not record usage" in capsys.readouterr().err


class TestAnswerCache:
    def test_expires_after_ttl(self):
        now = [0.0]
        cache = AnswerCache(ttl_seconds=10, clock=lambda: now[0])
        cache.put("k", "v")
        now[0] = 10
        assert cache.get("k") == "v"
        now[0] = 10.1
        assert cache.get("k") is None

    def test_evicts_least_recently_used(self):
        cache = AnswerCache(max_entries=2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")  # a is now fresher than b
        cache.put("c", 3)
        assert cache.get("b") is None
        assert cache.get("a") == 1 and cache.get("c") == 3

    def test_key_ignores_whitespace_but_not_language(self):
        assert cache_key(" Was ist\nBürgergeld? ", "de") == cache_key("Was ist Bürgergeld?", "de")
        assert cache_key("Was ist Bürgergeld?", "de") != cache_key("Was ist Bürgergeld?", "en")
