from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import AIUsage

# Standard API prices observed in September 2026. Keep this map explicit so a changed
# model or pricing plan never silently produces a wrong budget calculation.
TEXT_PRICING_PER_1M = {
    "gpt-6-astra": (10.0, 50.0),
    "gpt-5.6-sol": (4.0, 20.0),
    "gpt-5.6-terra": (2.0, 12.0),
    "gpt-5.6-luna": (0.20, 1.20),
}
EMBED_PRICING_PER_1M = {
    "text-embedding-3-small": 0.02,
    "text-embedding-3-large": 0.13,
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int = 0) -> float:
    if model in EMBED_PRICING_PER_1M:
        return round(input_tokens / 1_000_000 * EMBED_PRICING_PER_1M[model], 8)
    in_price, out_price = TEXT_PRICING_PER_1M.get(model, (0.0, 0.0))
    return round(input_tokens / 1_000_000 * in_price + output_tokens / 1_000_000 * out_price, 8)


def today_ai_cost(db: Session) -> float:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    value = db.query(func.coalesce(func.sum(AIUsage.estimated_cost_usd), 0.0)).filter(AIUsage.created_at >= start).scalar()
    return float(value or 0.0)


def can_use_paid_ai(db: Session) -> bool:
    settings = get_settings()
    return today_ai_cost(db) + settings.ai_budget_reserve_usd <= settings.daily_ai_budget_usd


def record_usage(db: Session, usage: dict | None) -> None:
    if not usage:
        return
    model = str(usage.get("model") or "unknown")
    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    db.add(
        AIUsage(
            provider="openai",
            model=model,
            operation=str(usage.get("operation") or "unknown"),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimate_cost(model, input_tokens, output_tokens),
        )
    )
