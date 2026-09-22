from __future__ import annotations

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.models import Article, Source, AIUsage
from app.db.session import get_db
from app.schemas.article import ArticleOut, PaginatedArticles
from app.services.analytics import signals, trends
from app.services.clients import load_clients
from app.services.digest import build_morning_digest
from app.services.ingestion import ingest_all
from app.services.search import keyword_search, semantic_search
from app.services.strategy_slide import build_strategy_slide
from app.services.ai_cost import today_ai_cost
from app.telegram.commands import handle_command
from app.telegram.bot import send_telegram

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)):
    return {"status": "ok", "articles": db.query(Article).count(), "sources": db.query(Source).count()}


@router.get("/articles", response_model=PaginatedArticles)
def articles(
    industry: str | None = None,
    topic: str | None = None,
    brand: str | None = None,
    min_score: float = 1.0,
    days: int = 30,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(Article).filter(Article.strategic_relevance_score >= min_score)
    q = q.filter(Article.collected_at >= datetime.now(timezone.utc) - timedelta(days=days))
    # JSON filtering is deliberately done in Python for SQLite/Postgres portability in MVP.
    rows = q.order_by(Article.strategic_relevance_score.desc(), Article.published_at.desc()).all()
    if industry:
        rows = [a for a in rows if industry in (a.industries or [])]
    if topic:
        rows = [a for a in rows if topic in (a.topics or [])]
    if brand:
        rows = [a for a in rows if brand.lower() in {b.lower() for b in (a.brands or [])}]
    total = len(rows)
    rows = rows[offset: offset + limit]
    return PaginatedArticles(items=[ArticleOut.model_validate(a) for a in rows], total=total, limit=limit, offset=offset)


@router.get("/articles/{article_id}", response_model=ArticleOut)
def article(article_id: int, db: Session = Depends(get_db)):
    row = db.get(Article, article_id)
    if not row:
        raise HTTPException(404, "Article not found")
    return row


@router.get("/search", response_model=list[ArticleOut])
def search(q: str, limit: int = 30, db: Session = Depends(get_db)):
    return keyword_search(db, q, limit)


@router.get("/search/semantic", response_model=list[ArticleOut])
async def search_semantic(q: str, limit: int = 20, db: Session = Depends(get_db)):
    return await semantic_search(db, q, limit)


@router.get("/trends")
def get_trends(days: int = 30, db: Session = Depends(get_db)):
    return trends(db, days=days)


@router.get("/signals")
def get_signals(days: int = 30, db: Session = Depends(get_db)):
    return signals(db, days=days)


@router.get("/clients")
def clients():
    return load_clients()


@router.get("/clients/{slug}/articles", response_model=list[ArticleOut])
def client_articles(slug: str, limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(Article).order_by(Article.strategic_relevance_score.desc()).limit(1000).all()
    matched = [a for a in rows if slug in (a.client_matches or {})]
    matched.sort(key=lambda a: a.client_matches[slug]["score"], reverse=True)
    return matched[:limit]


@router.get("/digest")
def digest(hours: int = 24, db: Session = Depends(get_db)):
    return {"markdown": build_morning_digest(db, hours=hours)}


@router.post("/collect")
async def collect(db: Session = Depends(get_db)):
    return {"results": await ingest_all(db)}


@router.get("/articles/{article_id}/strategy-slide")
def strategy_slide(article_id: int, db: Session = Depends(get_db)):
    row = db.get(Article, article_id)
    if not row:
        raise HTTPException(404, "Article not found")
    return build_strategy_slide(row)


@router.get("/sources/health")
def source_health(db: Session = Depends(get_db)):
    rows = db.query(Source).order_by(Source.priority.desc(), Source.name).all()
    return [
        {
            "name": s.name, "type": s.source_type, "enabled": s.enabled, "priority": s.priority,
            "reliability_score": s.reliability_score, "last_successful_fetch": s.last_successful_fetch,
            "failure_count": s.failure_count, "last_error": s.last_error,
        } for s in rows
    ]


@router.get("/ai/usage")
def ai_usage(db: Session = Depends(get_db)):
    return {"today_cost_usd": round(today_ai_cost(db), 6), "records": db.query(AIUsage).count()}


@router.post("/telegram/webhook")
async def telegram_webhook(update: dict, db: Session = Depends(get_db)):
    message = update.get("message") or update.get("edited_message") or {}
    text = message.get("text") or ""
    chat = message.get("chat") or {}
    if not text.startswith("/"):
        return {"ok": True}
    reply = handle_command(db, text)
    # send_telegram uses configured agency chat; webhook deployments can instead
    # set TELEGRAM_CHAT_ID to the same chat for a private/internal bot.
    await send_telegram(reply)
    return {"ok": True, "reply": reply}
