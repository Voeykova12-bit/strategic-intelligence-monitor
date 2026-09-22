from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.ai.provider import get_ai_provider
from app.ai.heuristic import HeuristicProvider
from app.collectors.rss import fetch_rss
from app.core.config import get_settings
from app.db.models import Article, Source, StoryCluster
from app.parsers.article import extract_article
from app.services.clients import score_client_matches
from app.services.ai_cost import can_use_paid_ai, record_usage
from app.services.dedup import canonicalize_url, likely_same_story
from app.services.prefilter import relevance_prefilter
from app.services.scoring import final_strategic_score
from app.services.source_registry import sync_sources

logger = logging.getLogger(__name__)


def _scope(source: Source) -> str:
    if source.country == "RU":
        return "Russia"
    if source.country in {"BY", "KZ", "AM", "AZ", "KG", "UZ", "TJ", "MD"}:
        return "CIS"
    return "Global"


def _find_cluster(db: Session, title: str) -> StoryCluster | None:
    since = datetime.now(timezone.utc) - timedelta(days=7)
    clusters = db.query(StoryCluster).filter(StoryCluster.latest_update >= since).order_by(StoryCluster.latest_update.desc()).limit(250).all()
    for cluster in clusters:
        if likely_same_story(title, cluster.title):
            return cluster
    return None


async def ingest_source(db: Session, source: Source) -> dict:
    settings = get_settings()
    stats = {"source": source.name, "fetched": 0, "created": 0, "duplicates": 0, "errors": 0}
    try:
        if source.source_type != "rss":
            raise NotImplementedError(f"Source type {source.source_type!r} is not implemented in MVP")
        items = await fetch_rss(source.url)
        stats["fetched"] = len(items)
        provider = get_ai_provider()

        for item in items:
            try:
                canonical = canonicalize_url(item.url)
                if db.query(Article).filter(Article.canonical_url == canonical).first():
                    stats["duplicates"] += 1
                    continue

                parsed = {"full_text": None, "author": item.author, "image_url": item.image_url}
                try:
                    parsed = await extract_article(item.url)
                except Exception as exc:
                    logger.info("Article extraction failed for %s: %s", item.url, exc)

                full_text = (parsed.get("full_text") or item.excerpt or "").strip()
                prefilter = relevance_prefilter(item.title, item.excerpt, source.topics)
                cluster = _find_cluster(db, item.title)
                if cluster is None:
                    cluster = StoryCluster(title=item.title, earliest_publication=item.published_at, latest_update=item.published_at or datetime.now(timezone.utc))
                    db.add(cluster)
                    db.flush()
                else:
                    stats["duplicates"] += 1
                    if item.published_at:
                        cluster.earliest_publication = min(filter(None, [cluster.earliest_publication, item.published_at]))
                        cluster.latest_update = max(filter(None, [cluster.latest_update, item.published_at]))

                article = Article(
                    source_id=source.id,
                    cluster_id=cluster.id,
                    title=item.title,
                    original_title=item.title,
                    url=item.url,
                    canonical_url=canonical,
                    source_name=source.name,
                    source_domain=urlparse(item.url).netloc.lower(),
                    published_at=item.published_at,
                    language=source.language,
                    country=source.country,
                    market_scope=_scope(source),
                    full_text=full_text,
                    excerpt=(item.excerpt or "")[:1200] or None,
                    author=parsed.get("author") or item.author,
                    image_url=parsed.get("image_url") or item.image_url,
                    source_quality_score=source.reliability_score,
                    prefilter_score=prefilter,
                )
                db.add(article)
                db.flush()
                if cluster.primary_article_id is None:
                    cluster.primary_article_id = article.id

                should_analyze = prefilter >= settings.min_relevance_before_llm or (source.priority >= 5 and prefilter >= settings.min_relevance_before_llm * 0.6)
                if should_analyze and full_text:
                    active_provider = provider
                    if provider.name == "openai" and not can_use_paid_ai(db):
                        active_provider = HeuristicProvider()
                    analysis = await active_provider.analyze(
                        title=item.title,
                        text=full_text,
                        source=source.name,
                        published_at=item.published_at.isoformat() if item.published_at else None,
                    )
                    article.summary = analysis.summary
                    article.strategic_summary = analysis.strategic_summary
                    article.why_it_matters = analysis.why_it_matters
                    article.implications = analysis.implications
                    article.industries = analysis.industries
                    article.subindustries = analysis.subindustries
                    article.topics = analysis.topics
                    article.brands = analysis.brands
                    article.companies = analysis.companies
                    article.products = analysis.products
                    article.people = analysis.people
                    article.platforms = analysis.platforms
                    article.technologies = analysis.technologies
                    article.locations = analysis.locations
                    article.keywords = analysis.keywords
                    article.sentiment = analysis.sentiment
                    article.trend_type = analysis.trend_type
                    article.event_type = analysis.event_type
                    article.novelty_score = analysis.novelty_score
                    article.confidence_score = analysis.confidence_score
                    article.llm_analyzed = active_provider.name == "openai"
                    article.ai_model = settings.openai_model if active_provider.name == "openai" else active_provider.name
                    if active_provider.name == "openai":
                        record_usage(db, getattr(active_provider, "last_usage", None))
                    article.client_matches = score_client_matches(item.title, full_text, analysis.brands, analysis.topics)
                    max_client_score = max((v["score"] for v in article.client_matches.values()), default=0)
                    corroboration = db.query(Article).filter(Article.cluster_id == cluster.id).count() + 1
                    article.strategic_relevance_score = final_strategic_score(
                        llm_score=analysis.strategic_relevance_score,
                        source_quality=source.reliability_score,
                        novelty=analysis.novelty_score,
                        corroborating_sources=corroboration,
                        client_relevance=max_client_score,
                    )
                    try:
                        if active_provider.name == "openai" and can_use_paid_ai(db):
                            article.embedding = await active_provider.embed(f"{item.title}\n{analysis.strategic_summary}\n{analysis.summary}")
                            record_usage(db, getattr(active_provider, "last_usage", None))
                    except Exception as exc:
                        logger.info("Embedding failed for article %s: %s", article.id, exc)
                else:
                    article.summary = item.excerpt[:500] if item.excerpt else None
                    article.strategic_relevance_score = max(1.0, round(source.reliability_score * 0.5 + prefilter * 2.0, 1))

                stats["created"] += 1
                db.commit()
            except Exception as exc:
                db.rollback()
                stats["errors"] += 1
                logger.exception("Failed item from %s: %s", source.name, exc)

        source.last_successful_fetch = datetime.now(timezone.utc)
        source.failure_count = 0
        source.last_error = None
        db.commit()
    except Exception as exc:
        db.rollback()
        source.failure_count = (source.failure_count or 0) + 1
        source.last_error = str(exc)[:2000]
        db.commit()
        stats["errors"] += 1
        logger.exception("Failed source %s", source.name)
    return stats


async def ingest_all(db: Session) -> list[dict]:
    sources = [s for s in sync_sources(db) if s.enabled]
    results = []
    for source in sources:
        results.append(await ingest_source(db, source))
        await asyncio.sleep(0.15)
    return results
