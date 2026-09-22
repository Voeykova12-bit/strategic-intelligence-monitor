from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import get_settings
from app.db.session import Base

settings = get_settings()

VectorType = None
if settings.database_url.startswith("postgresql"):
    try:
        from pgvector.sqlalchemy import Vector as _Vector

        VectorType = _Vector(1536)
    except Exception:
        VectorType = None


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    source_type: Mapped[str] = mapped_column(String(50), index=True)
    url: Mapped[str] = mapped_column(Text)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    country: Mapped[str | None] = mapped_column(String(10), nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    reliability_score: Mapped[float] = mapped_column(Float, default=3.0)
    priority: Mapped[int] = mapped_column(Integer, default=3)
    topics: Mapped[list] = mapped_column(JSON, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_successful_fetch: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class StoryCluster(Base):
    __tablename__ = "story_clusters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    primary_article_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    earliest_publication: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latest_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    articles = relationship("Article", back_populates="cluster", foreign_keys="Article.cluster_id")


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), nullable=True, index=True)
    cluster_id: Mapped[int | None] = mapped_column(ForeignKey("story_clusters.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(Text, index=True)
    original_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(Text)
    canonical_url: Mapped[str] = mapped_column(Text, unique=True, index=True)
    source_name: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    source_domain: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    country: Mapped[str | None] = mapped_column(String(20), nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    market_scope: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    strategic_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    why_it_matters: Mapped[str | None] = mapped_column(Text, nullable=True)
    implications: Mapped[list] = mapped_column(JSON, default=list)
    industries: Mapped[list] = mapped_column(JSON, default=list)
    subindustries: Mapped[list] = mapped_column(JSON, default=list)
    topics: Mapped[list] = mapped_column(JSON, default=list)
    brands: Mapped[list] = mapped_column(JSON, default=list)
    companies: Mapped[list] = mapped_column(JSON, default=list)
    products: Mapped[list] = mapped_column(JSON, default=list)
    people: Mapped[list] = mapped_column(JSON, default=list)
    platforms: Mapped[list] = mapped_column(JSON, default=list)
    technologies: Mapped[list] = mapped_column(JSON, default=list)
    locations: Mapped[list] = mapped_column(JSON, default=list)
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    sentiment: Mapped[str | None] = mapped_column(String(30), nullable=True)
    trend_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    event_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    strategic_relevance_score: Mapped[float] = mapped_column(Float, default=1.0, index=True)
    novelty_score: Mapped[float] = mapped_column(Float, default=1.0)
    source_quality_score: Mapped[float] = mapped_column(Float, default=3.0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    prefilter_score: Mapped[float] = mapped_column(Float, default=0.0)
    llm_analyzed: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    client_matches: Mapped[dict] = mapped_column(JSON, default=dict)

    if VectorType is not None:
        embedding: Mapped[list[float] | None] = mapped_column(VectorType, nullable=True)
    else:
        embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)

    source = relationship("Source")
    cluster = relationship("StoryCluster", back_populates="articles", foreign_keys=[cluster_id])


class AIUsage(Base):
    __tablename__ = "ai_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    provider: Mapped[str] = mapped_column(String(50), default="openai")
    model: Mapped[str] = mapped_column(String(100))
    operation: Mapped[str] = mapped_column(String(50))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
