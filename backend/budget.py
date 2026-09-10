"""Daily cap on OpenAI spend.

Per-IP rate limits can't bound total cost: many visitors (or one visitor
rotating IPs) still add up, and when the prepaid OpenAI balance runs out
every /chat call fails for everyone until someone tops it up (2026-09-10).
So /chat keeps a running total of what each OpenAI response actually cost,
computed from its token usage, and stops answering for the rest of the
UTC day once the total reaches DAILY_BUDGET_USD. Spending is then bounded
per day no matter where the traffic comes from.

The total lives in its own sqlite file (usage.db in DATA_DIR, see app/db.py)
so it survives restarts and redeploys. Accounting is approximate: concurrent
requests that pass the check together can each finish, so a day can end a
few cents over the cap.
"""

import os
import sys
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.engine import Engine

# USD per 1M tokens: (input, cached input, output). OpenAI list prices,
# 2026-09 (https://developers.openai.com/api/docs/pricing). Reasoning tokens
# are billed as output and are included in completion_tokens.
PRICES: dict[str, tuple[float, float, float]] = {
    "gpt-5.5": (5.00, 0.50, 30.00),
    "gpt-5.4-mini": (0.75, 0.075, 4.50),
    "gpt-5.4-nano": (0.20, 0.02, 1.25),
    "text-embedding-3-small": (0.02, 0.02, 0.0),
}
# A model missing from the table is costed like the most expensive one, so
# the cap errs towards stopping early rather than overspending.
FALLBACK_PRICE = max(PRICES.values(), key=lambda p: p[2])


def price_for(model: str) -> tuple[float, float, float]:
    # Longest matching prefix, so a dated snapshot ("gpt-5.5-2026-…") finds
    # its base model and "gpt-5.4-mini" never falls back to a shorter key.
    for name in sorted(PRICES, key=len, reverse=True):
        if model.startswith(name):
            return PRICES[name]
    print(f"[budget] no price for model {model!r}; costing it as the most expensive", file=sys.stderr)
    return FALLBACK_PRICE


def cost_usd(model: str, usage) -> float:
    """Cost of one response from its `usage` block (chat or embeddings)."""
    if usage is None:
        return 0.0
    input_price, cached_price, output_price = price_for(model)
    prompt = getattr(usage, "prompt_tokens", 0) or 0
    completion = getattr(usage, "completion_tokens", 0) or 0
    details = getattr(usage, "prompt_tokens_details", None)
    cached = min(getattr(details, "cached_tokens", 0) or 0, prompt)
    return (
        (prompt - cached) * input_price + cached * cached_price + completion * output_price
    ) / 1_000_000


def parse_limit(raw: str | None) -> float | None:
    """DAILY_BUDGET_USD: a dollar amount, or "off" to disable the cap."""
    if raw is None or raw.strip() == "":
        raw = "0.50"
    if raw.strip().lower() == "off":
        return None
    return float(raw)


def utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class DailyBudget:
    def __init__(self, engine: Engine, limit_usd: float | None, today=utc_day):
        self.engine = engine
        self.limit_usd = limit_usd
        self._today = today
        with self.engine.begin() as conn:
            conn.execute(text(
                "CREATE TABLE IF NOT EXISTS daily_spend ("
                " day TEXT PRIMARY KEY, usd REAL NOT NULL, calls INTEGER NOT NULL)"
            ))

    @classmethod
    def from_env(cls, engine: Engine) -> "DailyBudget":
        return cls(engine, parse_limit(os.environ.get("DAILY_BUDGET_USD")))

    def spent_today(self) -> float:
        with self.engine.connect() as conn:
            row = conn.execute(
                text("SELECT usd FROM daily_spend WHERE day = :day"), {"day": self._today()}
            ).first()
        return row[0] if row else 0.0

    def exhausted(self) -> bool:
        return self.limit_usd is not None and self.spent_today() >= self.limit_usd

    def record(self, model: str, usage) -> None:
        """Add one response's cost to today's total. Never raises: a broken
        usage.db must not turn a good answer into a 500."""
        try:
            usd = cost_usd(model, usage)
            if usd <= 0:
                return
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO daily_spend (day, usd, calls) VALUES (:day, :usd, 1) "
                        "ON CONFLICT(day) DO UPDATE SET usd = usd + excluded.usd, calls = calls + 1"
                    ),
                    {"day": self._today(), "usd": usd},
                )
        except Exception as exc:  # noqa: BLE001 - accounting must not break /chat
            print(f"[budget] could not record usage: {exc}", file=sys.stderr)
