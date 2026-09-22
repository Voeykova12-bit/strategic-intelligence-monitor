from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.db.models import Article


def _articles_since(db: Session, days: int) -> list[Article]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    return db.query(Article).filter(Article.collected_at >= since).all()


def trends(db: Session, days: int = 30, limit: int = 20) -> dict:
    now = datetime.now(timezone.utc)
    current_start = now - timedelta(days=days)
    previous_start = current_start - timedelta(days=days)
    current = db.query(Article).filter(Article.collected_at >= current_start).all()
    previous = db.query(Article).filter(Article.collected_at >= previous_start, Article.collected_at < current_start).all()

    def counters(rows):
        return (
            Counter(t for a in rows for t in (a.topics or [])),
            Counter(i for a in rows for i in (a.industries or [])),
            Counter(b for a in rows for b in (a.brands or [])),
        )

    topics, industries, brands = counters(current)
    prev_topics, prev_industries, prev_brands = counters(previous)

    def growth(current_counter, previous_counter):
        out = []
        for name, count in current_counter.items():
            prev = previous_counter.get(name, 0)
            if prev == 0:
                rate = None
            else:
                rate = round((count - prev) / prev * 100, 1)
            out.append({"name": name, "current": count, "previous": prev, "growth_pct": rate, "emerging": prev == 0 and count >= 2})
        out.sort(key=lambda x: (x["emerging"], x["growth_pct"] if x["growth_pct"] is not None else -999, x["current"]), reverse=True)
        return out[:limit]

    return {
        "period_days": days,
        "articles": len(current),
        "previous_articles": len(previous),
        "topics": topics.most_common(limit),
        "industries": industries.most_common(limit),
        "brands": brands.most_common(limit),
        "topic_growth": growth(topics, prev_topics),
        "industry_growth": growth(industries, prev_industries),
        "brand_growth": growth(brands, prev_brands),
        "emerging_topics": [x for x in growth(topics, prev_topics) if x["emerging"]],
    }


def signals(db: Session, days: int = 30, min_articles: int = 3, limit: int = 10) -> list[dict]:
    articles = _articles_since(db, days)
    buckets: dict[tuple[str, str], list[Article]] = {}
    for article in articles:
        for industry in article.industries or ["Other"]:
            for topic in article.topics or []:
                buckets.setdefault((industry, topic), []).append(article)
    result = []
    for (industry, topic), group in buckets.items():
        if len(group) < min_articles:
            continue
        top = sorted(group, key=lambda a: (a.strategic_relevance_score, a.published_at or a.collected_at), reverse=True)[:5]
        avg = sum(a.strategic_relevance_score for a in group) / len(group)
        result.append({
            "title": f"{topic}: растущая активность в {industry}",
            "description": f"За {days} дней зафиксировано {len(group)} релевантных материалов по теме {topic} в категории {industry}.",
            "industry": industry,
            "topic": topic,
            "article_count": len(group),
            "confidence": round(min(0.95, 0.45 + len(group) * 0.06 + avg * 0.04), 2),
            "strategic_implication": "Проверить, является ли активность устойчивым паттерном и как на него реагируют лидеры категории.",
            "supporting_articles": [{"id": a.id, "title": a.title, "url": a.url} for a in top],
        })
    result.sort(key=lambda x: (x["article_count"], x["confidence"]), reverse=True)
    return result[:limit]
