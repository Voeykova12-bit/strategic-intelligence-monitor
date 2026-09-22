from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

import httpx

from app.collectors.base import CollectedItem
from app.core.config import get_settings

try:
    import feedparser  # type: ignore
except Exception:  # pragma: no cover
    feedparser = None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None


def parse_rss_bytes(content: bytes) -> list[CollectedItem]:
    if feedparser is not None:
        parsed = feedparser.parse(content)
        items = []
        for e in parsed.entries:
            image = None
            if getattr(e, "media_content", None):
                image = e.media_content[0].get("url")
            items.append(
                CollectedItem(
                    title=getattr(e, "title", "").strip(),
                    url=getattr(e, "link", "").strip(),
                    published_at=_parse_dt(getattr(e, "published", None) or getattr(e, "updated", None)),
                    excerpt=getattr(e, "summary", None),
                    author=getattr(e, "author", None),
                    image_url=image,
                    raw=dict(e),
                )
            )
        return [i for i in items if i.title and i.url]

    root = ET.fromstring(content)
    items: list[CollectedItem] = []
    for node in root.findall(".//item"):
        title = (node.findtext("title") or "").strip()
        link = (node.findtext("link") or "").strip()
        if title and link:
            items.append(
                CollectedItem(
                    title=title,
                    url=link,
                    published_at=_parse_dt(node.findtext("pubDate")),
                    excerpt=node.findtext("description"),
                    author=node.findtext("author"),
                )
            )
    if not items:
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for node in root.findall(".//atom:entry", ns):
            title = (node.findtext("atom:title", default="", namespaces=ns) or "").strip()
            link_node = node.find("atom:link", ns)
            link = link_node.attrib.get("href", "").strip() if link_node is not None else ""
            if title and link:
                items.append(
                    CollectedItem(
                        title=title,
                        url=link,
                        published_at=_parse_dt(node.findtext("atom:updated", default=None, namespaces=ns)),
                        excerpt=node.findtext("atom:summary", default=None, namespaces=ns),
                    )
                )
    return items


async def fetch_rss(url: str) -> list[CollectedItem]:
    settings = get_settings()
    timeout = httpx.Timeout(settings.request_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers={"User-Agent": settings.user_agent}) as client:
        response = await client.get(url)
        response.raise_for_status()
        return parse_rss_bytes(response.content)[: settings.max_articles_per_source]
