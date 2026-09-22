from __future__ import annotations

import re
from urllib import robotparser
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.core.config import get_settings

try:
    import trafilatura  # type: ignore
except Exception:  # pragma: no cover
    trafilatura = None


def _clean_html_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header"]):
        tag.decompose()
    text = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
    return re.sub(r"\n{3,}", "\n\n", text)


async def robots_allowed(url: str) -> bool:
    settings = get_settings()
    if not settings.respect_robots:
        return True
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True, headers={"User-Agent": settings.user_agent}) as client:
            res = await client.get(robots_url)
        if res.status_code >= 400:
            return True
        rp = robotparser.RobotFileParser()
        rp.set_url(robots_url)
        rp.parse(res.text.splitlines())
        return rp.can_fetch(settings.user_agent, url)
    except Exception:
        return True


async def extract_article(url: str) -> dict:
    settings = get_settings()
    if not await robots_allowed(url):
        return {"full_text": None, "author": None, "image_url": None, "blocked_by_robots": True}

    async with httpx.AsyncClient(
        timeout=settings.request_timeout_seconds,
        follow_redirects=True,
        headers={"User-Agent": settings.user_agent},
    ) as client:
        res = await client.get(url)
        res.raise_for_status()
        html = res.text

    text = None
    if trafilatura is not None:
        try:
            text = trafilatura.extract(html, include_comments=False, include_tables=False, favor_precision=True)
        except Exception:
            text = None
    if not text:
        text = _clean_html_text(html)

    soup = BeautifulSoup(html, "html.parser")
    author = None
    author_meta = soup.find("meta", attrs={"name": re.compile("author", re.I)})
    if author_meta:
        author = author_meta.get("content")
    image_url = None
    image_meta = soup.find("meta", attrs={"property": "og:image"})
    if image_meta:
        image_url = image_meta.get("content")

    return {"full_text": text[:50000] if text else None, "author": author, "image_url": image_url, "blocked_by_robots": False}
