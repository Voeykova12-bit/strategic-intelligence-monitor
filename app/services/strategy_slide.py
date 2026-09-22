from __future__ import annotations

from app.db.models import Article


def build_strategy_slide(article: Article) -> dict:
    implications = article.implications or []
    return {
        "title": article.strategic_summary or article.title,
        "what_happened": article.summary or article.excerpt or article.title,
        "why_it_matters": implications[:3] if implications else [article.why_it_matters or "Событие меняет контекст категории и требует мониторинга."],
        "implication_for_brands": article.why_it_matters or (implications[0] if implications else "Оценить влияние на категорию, коммуникацию и медиастратегию."),
        "source": {"name": article.source_name or article.source_domain, "url": article.url, "date": article.published_at.isoformat() if article.published_at else None},
    }
