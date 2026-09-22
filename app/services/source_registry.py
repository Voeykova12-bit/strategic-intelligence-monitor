from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import yaml
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Source


def _resolve(path: str) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return get_settings().project_root / p


def load_source_config(path: str | None = None) -> list[dict]:
    settings = get_settings()
    cfg_path = _resolve(path or settings.source_config_path)
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    return data.get("sources", [])


def sync_sources(db: Session) -> list[Source]:
    configured = load_source_config()
    result: list[Source] = []
    for item in configured:
        src = db.query(Source).filter(Source.name == item["name"]).one_or_none()
        domain = urlparse(item["url"]).netloc.lower()
        if src is None:
            src = Source(name=item["name"], source_type=item["type"], url=item["url"])
            db.add(src)
        src.source_type = item["type"]
        src.url = item["url"]
        src.domain = item.get("domain") or domain
        src.country = item.get("country")
        src.language = item.get("language")
        src.reliability_score = float(item.get("reliability_score", 3))
        src.priority = int(item.get("priority", 3))
        src.topics = item.get("topics", [])
        src.enabled = bool(item.get("enabled", True))
        result.append(src)
    db.commit()
    for src in result:
        db.refresh(src)
    return result
