from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class NewsAnalysis:
    relevant: bool = True
    summary: str = ""
    strategic_summary: str = ""
    why_it_matters: str = ""
    implications: list[str] = field(default_factory=list)
    industries: list[str] = field(default_factory=list)
    subindustries: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    brands: list[str] = field(default_factory=list)
    companies: list[str] = field(default_factory=list)
    products: list[str] = field(default_factory=list)
    people: list[str] = field(default_factory=list)
    platforms: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    sentiment: str = "neutral"
    trend_type: str = ""
    event_type: str = ""
    strategic_relevance_score: float = 2.0
    novelty_score: float = 2.0
    confidence_score: float = 0.5


class AIProvider(ABC):
    name = "base"

    @abstractmethod
    async def analyze(self, *, title: str, text: str, source: str, published_at: str | None = None) -> NewsAnalysis:
        raise NotImplementedError

    async def embed(self, text: str) -> list[float] | None:
        return None
