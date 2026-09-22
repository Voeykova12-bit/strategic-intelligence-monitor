from __future__ import annotations

import hashlib
import html
import json
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

import feedparser
import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "news.json"
SOURCES_PATH = ROOT / "config" / "sources.yaml"
CLIENTS_PATH = ROOT / "config" / "clients.yaml"
USER_AGENT = "StrategicIntelligenceMonitor/1.0 (+GitHub Pages internal research)"
MAX_ITEMS = 1200

INDUSTRIES = {
    "Automotive": ["авто", "автомоб", "машин", "дилер", "haval", "chery", "geely", "changan", "москвич", "jetour", "tank", "tenet"],
    "Banking & Fintech": ["банк", "финтех", "кредит", "вклад", "ипотек", "карта", "платеж", "рассроч"],
    "Retail & E-commerce": ["ритейл", "маркетплейс", "e-commerce", "ecommerce", "ozon", "wildberries", "x5", "магнит", "лента"],
    "FMCG": ["fmcg", "напит", "продукт питания", "товары повседнев", "пиво"],
    "Technology": ["искусственн", "нейросет", "ai", "ии", "технолог", "software", "saas", "adtech", "martech"],
    "Telecom": ["телеком", "оператор связи", "мтс", "билайн", "мегафон", "t2"],
    "Pharma": ["фарма", "лекарств", "препарат"],
    "Beauty": ["космет", "beauty", "парфюм"],
    "Real Estate": ["недвижим", "девелоп", "жиль"],
    "Travel": ["туризм", "авиакомпан", "отель", "путешеств"],
    "Media & Advertising": ["реклам", "медиа", "marketing", "маркетинг", "бренд", "агентств"],
}

TOPICS = {
    "Advertising": ["реклам", "campaign", "кампан"],
    "Marketing": ["маркетинг", "marketing"],
    "Branding": ["бренд", "ребрендинг", "позиционирован"],
    "Product Launch": ["запустил", "запуск", "новый продукт", "новая модель", "представил"],
    "Pricing": ["цена", "подорож", "скидк", "тариф"],
    "Promotion": ["промо", "акци", "скидк"],
    "Consumer": ["потребител", "спрос", "поведен", "аудитор"],
    "Research": ["исследован", "опрос", "аналитик", "данные"],
    "Sponsorship": ["спонсор"],
    "Partnership": ["партнер", "партнёр", "коллаборац"],
    "Retail Media": ["retail media", "ритейл медиа"],
    "AI": [" ai ", " ии ", "искусственн", "нейросет", "генератив"],
    "Martech / Adtech": ["martech", "adtech", "programmatic"],
    "M&A": ["m&a", "слияни", "поглощен", "приобрел", "приобрёл"],
    "Investment": ["инвести", "раунд", "привлек"],
    "Financial Results": ["выручк", "прибыл", "ebitda", "финансовые результаты"],
}

KNOWN_BRANDS = ["Сбер", "ВТБ", "Альфа-Банк", "Яндекс", "VK", "Ozon", "Wildberries", "X5", "Магнит", "МТС", "МегаФон", "T2", "Москвич", "Haval", "Chery", "Geely", "Changan", "Jetour", "TENET", "TANK", "Балтика"]


def canonicalize(url: str) -> str:
    try:
        parts = urlsplit(url.strip())
        query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not k.lower().startswith("utm_") and k.lower() not in {"gclid", "yclid", "fbclid"}]
        return urlunsplit((parts.scheme.lower() or "https", parts.netloc.lower(), parts.path.rstrip("/") or "/", urlencode(sorted(query)), ""))
    except Exception:
        return url


def clean_text(value: str | None) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def parse_date(entry) -> str:
    raw = entry.get("published") or entry.get("updated") or ""
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def classify(text: str):
    low = f" {text.lower()} "
    industries = [name for name, words in INDUSTRIES.items() if any(w in low for w in words)]
    topics = [name for name, words in TOPICS.items() if any(w in low for w in words)]
    brands = [brand for brand in KNOWN_BRANDS if brand.lower() in low]
    if not industries:
        industries = ["Other"]
    if not topics:
        topics = ["Market Update"]
    return industries[:4], topics[:5], brands[:8]


def strategic_score(text: str, industries: list[str], topics: list[str], brands: list[str], priority: int, reliability: float) -> float:
    low = text.lower()
    high = ["запуск", "запуст", "инвести", "слияни", "поглощ", "партнер", "партнёр", "ребренд", "исследован", "продаж", "доля рынка", "цена", "реклам", "спонсор"]
    score = 1.2 + min(1.4, sum(1 for x in high if x in low) * 0.28)
    score += min(0.8, len(topics) * 0.16) + min(0.5, len(brands) * 0.15)
    score += max(0, min(0.5, (priority - 3) * 0.16))
    score += max(0, min(0.5, (reliability - 3) * 0.18))
    return round(max(1.0, min(5.0, score)), 1)


def why_it_matters(industries: list[str], topics: list[str], brands: list[str]) -> str:
    category = ", ".join(industries[:2])
    topic = ", ".join(topics[:2])
    if brands:
        return f"Сигнал по категории {category}: активность {', '.join(brands[:3])} может менять конкурентный и коммуникационный контекст. Тема: {topic}."
    return f"Сигнал по категории {category}. Стоит отслеживать развитие темы {topic} и реакцию игроков рынка."


def load_clients():
    data = yaml.safe_load(CLIENTS_PATH.read_text(encoding="utf-8")) or {}
    return data.get("clients", [])


def client_matches(text: str, clients: list[dict]) -> dict:
    low = text.lower()
    out = {}
    for c in clients:
        matched = []
        score = 0.0
        for term in c.get("brands", []):
            if term.lower() in low:
                matched.append(term); score += 2.0
        for term in c.get("competitors", []):
            if term.lower() in low:
                matched.append(term); score += 1.2
        if matched:
            out[c["slug"]] = {"name": c["name"], "score": round(min(5.0, 1.5 + score), 1), "matches": matched[:6]}
    return out


def fetch_source(src: dict, clients: list[dict]) -> list[dict]:
    if src.get("type") != "rss" or not src.get("enabled", True):
        return []
    req = Request(src["url"], headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/xml, */*"})
    with urlopen(req, timeout=25) as response:
        raw = response.read()
    feed = feedparser.parse(raw)
    result = []
    for entry in feed.entries[:40]:
        title = clean_text(entry.get("title"))
        url = canonicalize(entry.get("link", ""))
        summary = clean_text(entry.get("summary") or entry.get("description"))
        if not title or not url:
            continue
        combined = f"{title}. {summary}"
        industries, topics, brands = classify(combined)
        score = strategic_score(combined, industries, topics, brands, int(src.get("priority", 3)), float(src.get("reliability_score", 3)))
        uid = hashlib.sha1(f"{url}|{title.lower()}".encode("utf-8")).hexdigest()[:18]
        result.append({
            "id": uid,
            "title": title,
            "url": url,
            "source": src.get("name", "Source"),
            "published_at": parse_date(entry),
            "summary": summary[:620],
            "industries": industries,
            "topics": topics,
            "brands": brands,
            "score": score,
            "why_it_matters": why_it_matters(industries, topics, brands),
            "client_matches": client_matches(combined, clients),
            "market_scope": "Russia" if src.get("country") == "RU" else ("Global" if src.get("country") == "GLOBAL" else "CIS"),
        })
    return result


def main():
    sources = (yaml.safe_load(SOURCES_PATH.read_text(encoding="utf-8")) or {}).get("sources", [])
    clients = load_clients()
    if DATA_PATH.exists():
        try:
            previous = json.loads(DATA_PATH.read_text(encoding="utf-8")).get("items", [])
        except Exception:
            previous = []
    else:
        previous = []

    by_id = {item["id"]: item for item in previous if item.get("id")}
    errors = []
    for src in sources:
        try:
            for item in fetch_source(src, clients):
                by_id[item["id"]] = item
        except Exception as exc:
            errors.append({"source": src.get("name"), "error": str(exc)[:220]})
        time.sleep(0.15)

    items = list(by_id.values())
    items.sort(key=lambda x: x.get("published_at") or "", reverse=True)
    items = items[:MAX_ITEMS]
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_count": len(sources),
        "item_count": len(items),
        "errors": errors,
        "items": items,
    }
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Updated {len(items)} items from {len(sources)} sources; errors={len(errors)}")


if __name__ == "__main__":
    main()
