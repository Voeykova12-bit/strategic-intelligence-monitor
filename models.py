from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    url: str
    source_name: str | None = None
    source_domain: str | None = None
    published_at: datetime | None = None
    market_scope: str | None = None
    summary: str | None = None
    strategic_summary: str | None = None
    why_it_matters: str | None = None
    implications: list = Field(default_factory=list)
    industries: list = Field(default_factory=list)
    topics: list = Field(default_factory=list)
    brands: list = Field(default_factory=list)
    companies: list = Field(default_factory=list)
    strategic_relevance_score: float
    novelty_score: float
    confidence_score: float
    client_matches: dict = Field(default_factory=dict)


class PaginatedArticles(BaseModel):
    items: list[ArticleOut]
    total: int
    limit: int
    offset: int
