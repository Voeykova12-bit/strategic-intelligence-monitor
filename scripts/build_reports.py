from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "reports.json"
NEWS = ROOT / "data" / "news.json"
OUTPUT = ROOT / "data" / "reports.json"
UA = "StrategyRadar/1.0 (+research library)"

CATEGORY_MAP = {
    "Retail": "Ритейл",
    "DeliveryEcom": "Ритейл",
    "FMCG": "Ритейл",
    "Consumer": "Ритейл",
    "Automotive": "Авто",
    "RealEstate": "Недвижимость",
    "BanksFintech": "Банки",
    "FinanceEconomy": "Финансы",
    "MediaAdvertising": "Финансы",
}

def check_url(url: str) -> tuple[str, int | None]:
    if not url:
        return "missing", None
    try:
        req = Request(url, headers={"User-Agent": UA}, method="HEAD")
        with urlopen(req, timeout=7) as r:
            return ("ok" if int(r.status) < 400 else "unverified"), int(r.status)
    except Exception:
        try:
            req = Request(url, headers={"User-Agent": UA, "Range": "bytes=0-1024"})
            with urlopen(req, timeout=8) as r:
                return ("ok" if int(r.status) < 400 else "unverified"), int(r.status)
        except Exception:
            return "unverified", None

def report_category(item: dict) -> str | None:
    cats = item.get("categories") or []
    for c in cats:
        if c in CATEGORY_MAP:
            return CATEGORY_MAP[c]
    return CATEGORY_MAP.get(item.get("primary_category"))

def is_specific_url(url: str) -> bool:
    if not url or "://" not in url:
        return False
    after = url.split("://", 1)[1]
    path = after.split("/", 1)[1] if "/" in after else ""
    return len(path.strip("/")) >= 4

def auto_reports(news: dict, known_urls: set[str]) -> list[dict]:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=365)
    rows = []
    for item in news.get("items", []):
        try:
            published = datetime.fromisoformat((item.get("published_at") or "").replace("Z", "+00:00"))
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if published < cutoff:
            continue
        score = float(item.get("score", 0) or 0)
        source_quality = float(item.get("source_quality", 4.0) or 4.0)
        content_type = item.get("content_type")
        topics = item.get("topics") or []
        if content_type != "research" and "Исследования и прогнозы" not in topics:
            continue
        if score < 4.1 or source_quality < 4.2:
            continue
        url = item.get("url") or ""
        if url in known_urls or not is_specific_url(url):
            continue
        category = report_category(item)
        if not category:
            continue
        title = (item.get("title") or "").strip()
        if len(title) < 15:
            continue
        description = (item.get("summary") or item.get("why_it_matters") or "").strip()
        rows.append({
            "id": "auto-" + str(item.get("id", "")),
            "category": category,
            "title": title,
            "organization": (item.get("source") or "Источник").split("—")[0].strip(),
            "date": published.date().isoformat(),
            "description": description[:320],
            "url": url,
            "landing_url": url,
            "kind": "external_pdf" if url.lower().split("?")[0].endswith(".pdf") else "external_report",
            "access": "public",
            "source_item_id": item.get("id"),
            "strategic_relevance_score": item.get("strategic_relevance_score", int(round(score * 20))),
        })
        known_urls.add(url)
    rows.sort(key=lambda x: (x.get("strategic_relevance_score", 0), x.get("date", "")), reverse=True)
    per_category = {}
    selected = []
    for r in rows:
        cat = r["category"]
        if per_category.get(cat, 0) >= 5:
            continue
        selected.append(r)
        per_category[cat] = per_category.get(cat, 0) + 1
    return selected

def main() -> None:
    curated = json.loads(CONFIG.read_text(encoding="utf-8")).get("reports", [])
    try:
        news = json.loads(NEWS.read_text(encoding="utf-8"))
    except Exception:
        news = {"items": []}

    known = {r.get("url", "") for r in curated}
    reports = list(curated) + auto_reports(news, known)

    checked_at = datetime.now(timezone.utc).isoformat()
    for report in reports:
        status, http_status = check_url(report.get("url", ""))
        report["status"] = status
        report["http_status"] = http_status
        report["checked_at"] = checked_at

    reports.sort(key=lambda r: (r.get("category", ""), r.get("date", "")), reverse=True)
    payload = {
        "updated_at": checked_at,
        "report_count": len(reports),
        "categories": ["Ритейл", "Авто", "Недвижимость", "Банки", "Финансы"],
        "reports": reports,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Built {len(reports)} verified/specific research records")

if __name__ == "__main__":
    main()
