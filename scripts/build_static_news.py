from __future__ import annotations

import hashlib
import html
import json
import re
import time
from datetime import datetime, timedelta, timezone
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
USER_AGENT = "StrategicIntelligenceMonitor/2.0 (+GitHub Pages agency research)"
MAX_ITEMS = 5000
RETENTION_DAYS = 550
CORE_CATEGORIES = ["Retail", "Banks", "Finance", "FMCG"]

CATEGORY_KEYWORDS = {
    "Retail": ["ритейл", "рознич", "магазин", "торговая сеть", "торговых сет", "супермаркет", "дискаунтер", "маркетплейс", "e-commerce", "ecommerce", "онлайн-торгов", "доставка", "пвз", "x5", "пятёроч", "пятероч", "перекрёст", "чижик", "магнит", "лента", "вкусвилл", "ozon", "wildberries", "ашан", "лемана про"],
    "Banks": ["банк", "банков", "кредит", "вклад", "депозит", "ипотек", "карта", "эквайр", "альфа-банк", "альфа банк", "сбер", "втб", "т-банк", "тинькофф"],
    "Finance": ["финанс", "центробанк", "центральный банк", "ключевая ставка", "ставк", "инфляц", "рубл", "валют", "курс доллар", "бирж", "облигац", "инвести", "финрын", "платеж", "платёж", "рассроч", "bnpl", "акци", "дивиденд", "капитал"],
    "FMCG": ["fmcg", "продукт", "напит", "еда", "готовая еда", "food", "молоч", "мяс", "кофе", "чай", "снек", "кондитер", "космет", "бытовая хим", "товары повседнев", "производитель продуктов", "бакале", "заморож", "напитки"],
}

TOPIC_KEYWORDS = {
    "Consumer": ["потребител", "покупател", "спрос", "поведен", "лояльност", "аудитор"],
    "Pricing": ["цена", "цены", "подорож", "дешев", "скидк", "тариф", "инфляц"],
    "Promotion": ["промо", "акци", "скидк", "кэшбэк", "кешбэк"],
    "Advertising": ["реклам", "кампан", "медиаразмещ", "ролик"],
    "Branding": ["бренд", "ребрендинг", "позиционирован", "айдентик"],
    "Retail Media": ["retail media", "ритейл медиа", "ритейл-медиа"],
    "Product Launch": ["запустил", "запускает", "запуск", "новый продукт", "новый сервис", "представил"],
    "Expansion": ["открыл", "открыла", "открытие", "расшир", "новые магазины", "новые точки"],
    "Research": ["исследован", "опрос", "аналитик", "данные показали", "по данным"],
    "Partnership": ["партнер", "партнёр", "коллаборац", "сотрудничеств"],
    "Technology": ["искусственн", "нейросет", " ии ", " ai ", "технолог", "автоматизац"],
    "Regulation": ["закон", "регулирован", "цб ", "фас ", "минфин", "маркировк", "налог"],
    "M&A / Investment": ["слияни", "поглощ", "приобрел", "приобрёл", "сделк", "инвести", "раунд"],
    "Financial Results": ["выручк", "прибыл", "ebitda", "оборот", "финансовые результаты"],
}

KNOWN_BRANDS = [
    "X5", "Пятёрочка", "Пятерочка", "Перекрёсток", "Перекресток", "Чижик", "Магнит", "Лента", "ВкусВилл", "Ozon", "Wildberries",
    "Альфа-Банк", "Сбер", "ВТБ", "Т-Банк", "Яндекс", "VK", "МТС", "МегаФон", "Балтика", "PepsiCo", "Nestle", "Unilever", "Mars", "Mondelez"
]

FOREIGN_MARKERS = ["сша", "америк", "евросоюз", "европ", "китай", "китайск", "индия", "турц", "оаэ", "британи", "германи", "франци", "итал", "испан", "япони", "коре", "global", "worldwide", "международн"]
RUSSIA_MARKERS = ["россия", "россий", " рф ", "москв", "петербург", "рубл", "цб росс", "x5", "пятёроч", "чижик", "альфа-банк"]
FUTURE_RE = re.compile(r"\b(2027|2028|2029|2030|2031|2032|2033|2034|2035)\b")
FUTURE_WORDS = ["планирует", "планируют", "планируется", "намерен", "намерена", "к 2027", "до 2030", "в следующем году", "прогнозирует", "прогноз"]


def canonicalize(url: str) -> str:
    try:
        parts = urlsplit(url.strip())
        query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not k.lower().startswith("utm_") and k.lower() not in {"gclid", "yclid", "fbclid", "from", "ref"}]
        return urlunsplit((parts.scheme.lower() or "https", parts.netloc.lower(), parts.path.rstrip("/") or "/", urlencode(sorted(query)), ""))
    except Exception:
        return url


def clean_text(value: str | None) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def compact_summary(value: str, limit: int = 360) -> str:
    text = clean_text(value)
    if len(text) <= limit:
        return text
    cut = text[:limit]
    pos = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return (cut[:pos + 1] if pos > 150 else cut.rstrip()) + "…"


def parse_date(entry) -> str:
    raw = entry.get("published") or entry.get("updated") or ""
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def classify(text: str, source_name: str) -> tuple[list[str], list[str], list[str]]:
    low = f" {text.lower()} "
    categories = [name for name, words in CATEGORY_KEYWORDS.items() if any(w in low for w in words)]
    if source_name.startswith("Retail.ru") and "Retail" not in categories:
        categories.append("Retail")
    if source_name.startswith("Банки.ру"):
        if "Banks" not in categories:
            categories.append("Banks")
        if "Finance" not in categories:
            categories.append("Finance")
    topics = [name for name, words in TOPIC_KEYWORDS.items() if any(w in low for w in words)]
    brands = [brand for brand in KNOWN_BRANDS if brand.lower() in low]
    return categories[:4], (topics or ["Market Development"])[:6], list(dict.fromkeys(brands))[:10]


def detect_scope(text: str) -> str:
    low = f" {text.lower()} "
    ru = sum(1 for m in RUSSIA_MARKERS if m in low)
    foreign = sum(1 for m in FOREIGN_MARKERS if m in low)
    return "Global" if foreign > ru else "Russia"


def planning_horizon(text: str) -> list[str]:
    low = text.lower()
    years = FUTURE_RE.findall(text)
    if years or any(x in low for x in FUTURE_WORDS):
        return list(dict.fromkeys(years)) or ["future"]
    return []


def strategic_score(text: str, categories: list[str], topics: list[str], brands: list[str], priority: int, reliability: float, future: list[str]) -> float:
    low = text.lower()
    high = ["запуск", "инвести", "слияни", "поглощ", "партнер", "партнёр", "ребренд", "исследован", "продаж", "доля рынка", "цена", "выручк", "прибыл", "регулирован", "маркировк"]
    score = 1.7 + min(1.3, sum(1 for x in high if x in low) * 0.24)
    score += min(0.55, len(topics) * 0.10) + min(0.45, len(brands) * 0.12)
    score += max(0, min(0.45, (priority - 3) * 0.15)) + max(0, min(0.35, (reliability - 3) * 0.14))
    if len(categories) > 1:
        score += 0.15
    if future:
        score += 0.25
    return round(max(1.0, min(5.0, score)), 1)


def why_it_matters(categories: list[str], topics: list[str], brands: list[str], future: list[str]) -> str:
    cat = categories[0] if categories else "рынка"
    topic = ", ".join(topics[:2])
    base = {
        "Retail": "Может влиять на конкурентную динамику сетей, ассортимент, цены, промо и покупательское поведение.",
        "Banks": "Может влиять на банковские офферы, клиентское поведение, лояльность и коммуникационную активность.",
        "Finance": "Меняет финансовый контекст для потребителей и бизнеса: стоимость денег, спрос, инвестиции или платежное поведение.",
        "FMCG": "Может влиять на спрос, цены, продуктовый портфель, дистрибуцию и коммуникацию FMCG-брендов.",
    }.get(cat, "Может менять конкурентный и потребительский контекст категории.")
    if brands:
        base += f" В материале фигурируют: {', '.join(brands[:3])}."
    if future:
        base += f" Есть ориентир на будущий период: {', '.join(future)}."
    return f"{base} Тема: {topic}."


def load_clients() -> list[dict]:
    return (yaml.safe_load(CLIENTS_PATH.read_text(encoding="utf-8")) or {}).get("clients", [])


def client_matches(text: str, clients: list[dict]) -> dict:
    low = text.lower()
    out = {}
    for c in clients:
        matched = [term for term in c.get("brands", []) if term.lower() in low]
        if matched:
            out[c["slug"]] = {"name": c["name"], "score": round(min(5.0, 2.5 + len(matched) * 0.5), 1), "matches": matched[:6]}
    return out


def title_key(title: str) -> str:
    s = re.sub(r"[^a-zа-яё0-9 ]+", " ", title.lower())
    return " ".join(s.split())[:180]


def fetch_source(src: dict, clients: list[dict]) -> list[dict]:
    if src.get("type") != "rss" or not src.get("enabled", True) or not src.get("accessible_without_vpn_ru", False):
        return []
    req = Request(src["url"], headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/xml, */*"})
    with urlopen(req, timeout=30) as response:
        raw = response.read()
    feed = feedparser.parse(raw)
    result = []
    for entry in feed.entries[:100]:
        title = clean_text(entry.get("title"))
        url = canonicalize(entry.get("link", ""))
        summary_raw = entry.get("summary") or entry.get("description") or ""
        summary = compact_summary(summary_raw)
        if not title or not url:
            continue
        combined = f"{title}. {clean_text(summary_raw)}"
        categories, topics, brands = classify(combined, src.get("name", ""))
        if not categories:
            continue
        future = planning_horizon(combined)
        score = strategic_score(combined, categories, topics, brands, int(src.get("priority", 3)), float(src.get("reliability_score", 3)), future)
        uid = hashlib.sha1(f"{url}|{title_key(title)}".encode("utf-8")).hexdigest()[:18]
        result.append({
            "id": uid,
            "title": title,
            "url": url,
            "source": src.get("name", "Source"),
            "published_at": parse_date(entry),
            "summary": summary,
            "categories": categories,
            "primary_category": categories[0],
            "topics": topics,
            "brands": brands,
            "score": score,
            "why_it_matters": why_it_matters(categories, topics, brands, future),
            "client_matches": client_matches(combined, clients),
            "market_scope": detect_scope(combined),
            "future_horizon": future,
        })
    return result


def main():
    sources = (yaml.safe_load(SOURCES_PATH.read_text(encoding="utf-8")) or {}).get("sources", [])
    sources = [s for s in sources if s.get("accessible_without_vpn_ru", False)]
    clients = load_clients()
    active_sources = {s["name"] for s in sources}
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)

    previous = []
    if DATA_PATH.exists():
        try:
            previous = json.loads(DATA_PATH.read_text(encoding="utf-8")).get("items", [])
        except Exception:
            previous = []

    by_id = {}
    title_seen = {}
    for item in previous:
        try:
            published = datetime.fromisoformat(item.get("published_at", "").replace("Z", "+00:00"))
        except Exception:
            continue
        if item.get("source") not in active_sources or published < cutoff or not item.get("categories"):
            continue
        by_id[item["id"]] = item
        title_seen[title_key(item.get("title", ""))] = item["id"]

    errors = []
    source_stats = []
    for src in sources:
        count = 0
        try:
            for item in fetch_source(src, clients):
                key = title_key(item["title"])
                old_id = title_seen.get(key)
                if old_id and old_id in by_id:
                    old = by_id[old_id]
                    if item["score"] > old.get("score", 0):
                        by_id.pop(old_id, None)
                    else:
                        continue
                by_id[item["id"]] = item
                title_seen[key] = item["id"]
                count += 1
        except Exception as exc:
            errors.append({"source": src.get("name"), "error": str(exc)[:220]})
        source_stats.append({"source": src.get("name"), "added": count})
        time.sleep(0.12)

    items = list(by_id.values())
    items.sort(key=lambda x: x.get("published_at") or "", reverse=True)
    items = items[:MAX_ITEMS]
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_count": len(sources),
        "item_count": len(items),
        "retention_days": RETENTION_DAYS,
        "core_categories": CORE_CATEGORIES,
        "clients": [{"slug": c["slug"], "name": c["name"]} for c in clients],
        "source_stats": source_stats,
        "errors": errors,
        "items": items,
    }
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Updated {len(items)} relevant items from {len(sources)} Russia-accessible sources; errors={len(errors)}")


if __name__ == "__main__":
    main()
