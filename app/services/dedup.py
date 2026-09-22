from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "yclid", "fbclid", "from", "ref"
}


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in TRACKING_PARAMS]
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    if path != "/":
        path = path.rstrip("/")
    host = (parts.hostname or "").lower()
    port = f":{parts.port}" if parts.port and not ((parts.scheme == "http" and parts.port == 80) or (parts.scheme == "https" and parts.port == 443)) else ""
    netloc = host + port
    return urlunsplit((parts.scheme.lower() or "https", netloc, path, urlencode(sorted(query)), ""))


def normalize_title(title: str) -> str:
    value = unicodedata.normalize("NFKC", title).lower().replace("ё", "е")
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def title_similarity(a: str, b: str) -> float:
    na, nb = normalize_title(a), normalize_title(b)
    if not na or not nb:
        return 0.0
    seq = SequenceMatcher(None, na, nb).ratio()
    sa, sb = set(na.split()), set(nb.split())
    jaccard = len(sa & sb) / max(1, len(sa | sb))
    return max(seq, jaccard)


def likely_same_story(a: str, b: str, threshold: float = 0.76) -> bool:
    return title_similarity(a, b) >= threshold
