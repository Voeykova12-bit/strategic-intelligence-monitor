from __future__ import annotations

import json

import httpx

from app.ai.base import AIProvider, NewsAnalysis
from app.core.config import get_settings

ANALYSIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "relevant": {"type": "boolean"},
        "summary": {"type": "string"},
        "strategic_summary": {"type": "string"},
        "why_it_matters": {"type": "string"},
        "implications": {"type": "array", "items": {"type": "string"}},
        "industries": {"type": "array", "items": {"type": "string"}},
        "subindustries": {"type": "array", "items": {"type": "string"}},
        "topics": {"type": "array", "items": {"type": "string"}},
        "brands": {"type": "array", "items": {"type": "string"}},
        "companies": {"type": "array", "items": {"type": "string"}},
        "products": {"type": "array", "items": {"type": "string"}},
        "people": {"type": "array", "items": {"type": "string"}},
        "platforms": {"type": "array", "items": {"type": "string"}},
        "technologies": {"type": "array", "items": {"type": "string"}},
        "locations": {"type": "array", "items": {"type": "string"}},
        "keywords": {"type": "array", "items": {"type": "string"}},
        "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative", "mixed"]},
        "trend_type": {"type": "string"},
        "event_type": {"type": "string"},
        "strategic_relevance_score": {"type": "number", "minimum": 1, "maximum": 5},
        "novelty_score": {"type": "number", "minimum": 1, "maximum": 5},
        "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": [
        "relevant", "summary", "strategic_summary", "why_it_matters", "implications", "industries", "subindustries",
        "topics", "brands", "companies", "products", "people", "platforms", "technologies", "locations", "keywords",
        "sentiment", "trend_type", "event_type", "strategic_relevance_score", "novelty_score", "confidence_score"
    ],
}

SYSTEM_PROMPT = """Ты аналитический модуль для стратегического отдела рекламного агентства.
Анализируй деловые, отраслевые, маркетинговые, медийные и технологические новости.
Не пересказывай материал целиком. Определи, что изменилось на рынке, почему это может быть значимо для брендов,
коммуникации, медиастратегии и поведения потребителей. Будь консервативен: не выдумывай факты, которых нет в тексте.
Summary — максимум 2–3 предложения. Strategic summary — значение события для рынка. Implications — конкретные последствия.
Strategic relevance: 1 шум, 2 контекст, 3 заметный сигнал, 4 существенное изменение, 5 событие, потенциально требующее реакции.
"""


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.last_usage: dict = {}
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")

    async def analyze(self, *, title: str, text: str, source: str, published_at: str | None = None) -> NewsAnalysis:
        payload = {
            "model": self.settings.openai_model,
            "instructions": SYSTEM_PROMPT,
            "input": f"SOURCE: {source}\nPUBLISHED: {published_at or 'unknown'}\nTITLE: {title}\n\nTEXT:\n{text[:18000]}",
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "news_analysis",
                    "strict": True,
                    "schema": ANALYSIS_SCHEMA,
                }
            },
        }
        headers = {"Authorization": f"Bearer {self.settings.openai_api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=60) as client:
            res = await client.post("https://api.openai.com/v1/responses", headers=headers, json=payload)
            res.raise_for_status()
            body = res.json()
        output_text = body.get("output_text")
        if not output_text:
            chunks = []
            for item in body.get("output", []):
                for content in item.get("content", []):
                    if content.get("type") == "output_text":
                        chunks.append(content.get("text", ""))
            output_text = "".join(chunks)
        usage = body.get("usage") or {}
        self.last_usage = {
            "operation": "analysis",
            "model": self.settings.openai_model,
            "input_tokens": int(usage.get("input_tokens", 0) or 0),
            "output_tokens": int(usage.get("output_tokens", 0) or 0),
        }
        data = json.loads(output_text)
        return NewsAnalysis(**data)

    async def embed(self, text: str) -> list[float] | None:
        payload = {"model": self.settings.openai_embedding_model, "input": text[:12000]}
        headers = {"Authorization": f"Bearer {self.settings.openai_api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post("https://api.openai.com/v1/embeddings", headers=headers, json=payload)
            res.raise_for_status()
        body = res.json()
        usage = body.get("usage") or {}
        self.last_usage = {
            "operation": "embedding",
            "model": self.settings.openai_embedding_model,
            "input_tokens": int(usage.get("prompt_tokens", usage.get("total_tokens", 0)) or 0),
            "output_tokens": 0,
        }
        return body["data"][0]["embedding"]
