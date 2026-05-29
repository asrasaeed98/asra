"""Monthly Anthropic spend ledger + budget guard.

Tracks estimated token cost per calendar month so we can stop calling the model
(and degrade gracefully) before blowing through a configured budget.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from findings_api.config import settings
from findings_api.models import ApiUsage

logger = logging.getLogger(__name__)

# USD per 1,000,000 tokens (input, output). Verify against current Anthropic pricing.
PRICING: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-sonnet-4-6": (3.0, 15.0),
}
_DEFAULT_PRICE = (3.0, 15.0)

BUDGET_MESSAGE = (
    "Sorry, we've run out of AI budget for now :( "
    "The assistant is paused until the monthly limit resets. "
    "Your analysis and results above are still fully available."
)


def estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    price_in, price_out = PRICING.get(model, _DEFAULT_PRICE)
    return (tokens_in / 1_000_000) * price_in + (tokens_out / 1_000_000) * price_out


def month_key(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return now.strftime("%Y-%m")


def current_month_cost(db: Session) -> float:
    row = db.get(ApiUsage, month_key())
    return float(row.cost_usd) if row else 0.0


def is_over_budget(db: Session) -> bool:
    budget = settings.ai_monthly_budget_usd
    if budget is None or budget <= 0:
        return False
    try:
        return current_month_cost(db) >= budget
    except Exception:
        logger.exception("Budget check failed; allowing AI call")
        return False


def record_usage(db: Session, model: str, tokens_in: int, tokens_out: int) -> None:
    """Add a call's token spend to the current month's ledger (best-effort)."""
    tokens_in = int(tokens_in or 0)
    tokens_out = int(tokens_out or 0)
    if tokens_in == 0 and tokens_out == 0:
        return
    try:
        key = month_key()
        row = db.get(ApiUsage, key)
        if row is None:
            row = ApiUsage(month=key, tokens_in=0, tokens_out=0, cost_usd=0.0, calls=0)
            db.add(row)
        row.tokens_in = int(row.tokens_in or 0) + tokens_in
        row.tokens_out = int(row.tokens_out or 0) + tokens_out
        row.cost_usd = float(row.cost_usd or 0.0) + estimate_cost(model, tokens_in, tokens_out)
        row.calls = int(row.calls or 0) + 1
        db.commit()
    except Exception:
        logger.exception("Failed to record AI usage")
        db.rollback()
