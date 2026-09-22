from __future__ import annotations

import math
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from app.ai.provider import get_ai_provider
from app.core.config import get_settings
from app.db.models import Article


def keyword_search(db: Session, q: str, limit: int = 30) -> list[Article]:
    like = f"%{q}%"
    return (
        db.query(Article)
        .filter(or_(Article.title.ilike(like), Article.full_text.ilike(like), Article.summary.ilike(like), Article.strategic_summary.ilike(like)))
        .order_by(Article.strategic_relevance_score.desc(), Article.published_at.desc())
        .limit(limit)
        .all()
    )


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


async def semantic_search(db: Session, q: str, limit: int = 20) -> list[Article]:
    provider = get_ai_provider()
    vector = await provider.embed(q)
    if not vector:
        return keyword_search(db, q, limit)
    settings = get_settings()
    if settings.database_url.startswith("postgresql"):
        rows = db.execute(
            text("SELECT id FROM articles WHERE embedding IS NOT NULL ORDER BY embedding <=> CAST(:vec AS vector) LIMIT :lim"),
            {"vec": str(vector), "lim": limit},
        ).fetchall()
        ids = [r[0] for r in rows]
        by_id = {a.id: a for a in db.query(Article).filter(Article.id.in_(ids)).all()}
        return [by_id[i] for i in ids if i in by_id]
    candidates = db.query(Article).filter(Article.embedding.isnot(None)).limit(1000).all()
    scored = [(_cosine(vector, a.embedding), a) for a in candidates if isinstance(a.embedding, list)]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [a for _, a in scored[:limit]]
