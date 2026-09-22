from __future__ import annotations

from pathlib import Path
import yaml

from app.core.config import get_settings


def load_clients() -> list[dict]:
    settings = get_settings()
    path = Path(settings.client_config_path)
    if not path.is_absolute():
        path = settings.project_root / path
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("clients", [])


def score_client_matches(title: str, text: str, brands: list[str] | None = None, topics: list[str] | None = None) -> dict:
    haystack = f"{title}\n{text}".lower()
    brands_lower = {b.lower() for b in (brands or [])}
    topics_lower = {t.lower() for t in (topics or [])}
    matches = {}
    for client in load_clients():
        score = 0.0
        reasons = []
        client_terms = client.get("brands", []) + client.get("competitors", [])
        for term in client_terms:
            if term.lower() in haystack or term.lower() in brands_lower:
                score += 1.5 if term in client.get("brands", []) else 1.0
                reasons.append(term)
        for topic in client.get("track", []):
            if topic.lower() in haystack or topic.lower() in topics_lower:
                score += 0.35
        if score > 0:
            matches[client["slug"]] = {"score": min(5.0, round(1.0 + score, 1)), "reasons": reasons[:8]}
    return matches
