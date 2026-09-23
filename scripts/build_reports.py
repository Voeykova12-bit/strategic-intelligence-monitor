from __future__ import annotations

import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "reports.json"
NEWS = ROOT / "data" / "news.json"
OUTPUT = ROOT / "data" / "reports.json"
ARCHIVE_DIR = ROOT / "docs" / "reports"
UA = "StrategyRadar/1.0 (+research library)"
MAX_ARCHIVE_BYTES = 40 * 1024 * 1024

CATEGORY_MAP = {
    "Retail": "Ритейл", "DeliveryEcom": "Ритейл", "FMCG": "Ритейл", "Consumer": "Ритейл",
    "Automotive": "Авто", "RealEstate": "Недвижимость",
    "BanksFintech": "Банки", "FinanceEconomy": "Финансы", "MediaAdvertising": "Финансы",
}

def request(url: str, method: str = "GET", timeout: int = 12):
    return urlopen(Request(url, headers={"User-Agent": UA, "Accept": "*/*"}, method=method), timeout=timeout)

def check_url(url: str) -> tuple[str, int | None]:
    if not url:
        return "missing", None
    try:
        with request(url, "HEAD", 8) as r:
            code = int(r.status)
            return ("ok" if code < 400 else "unverified"), code
    except Exception:
        try:
            req = Request(url, headers={"User-Agent": UA, "Range": "bytes=0-1024", "Accept": "*/*"})
            with urlopen(req, timeout=10) as r:
                code = int(r.status)
                return ("ok" if code < 400 else "unverified"), code
        except Exception:
            return "unverified", None

def specific_url(url: str) -> bool:
    if not url or "://" not in url:
        return False
    after = url.split("://", 1)[1]
    path = after.split("/", 1)[1] if "/" in after else ""
    return len(path.strip("/")) >= 4

def category_for(item: dict) -> str | None:
    for c in item.get("categories") or []:
        if c in CATEGORY_MAP:
            return CATEGORY_MAP[c]
    return CATEGORY_MAP.get(item.get("primary_category"))

def auto_reports(news: dict, known_urls: set[str]) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=365)
    candidates = []
    for item in news.get("items", []):
        try:
            published = datetime.fromisoformat((item.get("published_at") or "").replace("Z", "+00:00"))
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if published < cutoff:
            continue
        score = int(item.get("strategic_relevance_score") or round(float(item.get("score", 0) or 0) * 20))
        quality = float(item.get("source_quality", 4.0) or 4.0)
        ctype = item.get("content_type")
        topics = item.get("topics") or []
        if ctype != "research" and "Исследования и прогнозы" not in topics:
            continue
        if score < 82 or quality < 4.2:
            continue
        url = item.get("url") or ""
        if url in known_urls or not specific_url(url):
            continue
        category = category_for(item)
        if not category:
            continue
        title = (item.get("title") or "").strip()
        if len(title) < 15:
            continue
        candidates.append({
            "id": "auto-" + str(item.get("id", "")),
            "category": category,
            "title": title,
            "organization": (item.get("source") or "Источник").split("—")[0].strip(),
            "date": published.date().isoformat(),
            "description": (item.get("summary") or item.get("why_it_matters") or "").strip()[:340],
            "url": url,
            "landing_url": url,
            "kind": "external_pdf" if url.lower().split("?")[0].endswith(".pdf") else "external_report",
            "access": "public",
            "source_item_id": item.get("id"),
            "strategic_relevance_score": score,
        })
        known_urls.add(url)
    candidates.sort(key=lambda x: (x.get("strategic_relevance_score", 0), x.get("date", "")), reverse=True)
    per_category, selected = {}, []
    for r in candidates:
        if per_category.get(r["category"], 0) >= 6:
            continue
        selected.append(r)
        per_category[r["category"]] = per_category.get(r["category"], 0) + 1
    return selected

def safe_name(report_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", report_id).strip("-") + ".pdf"

def archive_pdf(report: dict) -> tuple[bool, str]:
    if not report.get("archive") or report.get("access") != "public":
        return False, ""
    url = report.get("url") or ""
    if not url.lower().split("?")[0].endswith(".pdf"):
        return False, ""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    name = safe_name(report.get("id") or "report")
    path = ARCHIVE_DIR / name
    try:
        with request(url, "GET", 30) as r:
            content_type = (r.headers.get("Content-Type") or "").lower()
            length = int(r.headers.get("Content-Length") or 0)
            if length and length > MAX_ARCHIVE_BYTES:
                return False, "too_large"
            data = r.read(MAX_ARCHIVE_BYTES + 1)
            if len(data) > MAX_ARCHIVE_BYTES:
                return False, "too_large"
            if not data.startswith(b"%PDF") and "pdf" not in content_type:
                return False, "not_pdf"
            path.write_bytes(data)
        report["local_path"] = "reports/" + name
        report["kind"] = "local_pdf"
        report["archived_at"] = datetime.now(timezone.utc).isoformat()
        return True, ""
    except Exception as e:
        return False, str(e)[:180]

def main() -> None:
    curated = json.loads(CONFIG.read_text(encoding="utf-8")).get("reports", [])
    try:
        news = json.loads(NEWS.read_text(encoding="utf-8"))
    except Exception:
        news = {"items": []}

    known = {r.get("url", "") for r in curated}
    reports = list(curated) + auto_reports(news, known)
    checked_at = datetime.now(timezone.utc).isoformat()
    archive_errors = []

    for report in reports:
        status, http_status = check_url(report.get("url", ""))
        report["status"] = status
        report["http_status"] = http_status
        report["checked_at"] = checked_at
        ok, err = archive_pdf(report)
        if report.get("archive") and not ok and err:
            archive_errors.append({"id": report.get("id"), "error": err})

    reports = [r for r in reports if r.get("status") == "ok" or r.get("access") == "paid"]
    reports.sort(key=lambda r: (r.get("category", ""), r.get("date", "")), reverse=True)
    payload = {
        "updated_at": checked_at,
        "report_count": len(reports),
        "categories": ["Ритейл", "Авто", "Недвижимость", "Банки", "Финансы"],
        "reports": reports,
        "archive_errors": archive_errors,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Built {len(reports)} specific research records; archived={sum(1 for r in reports if r.get('kind')=='local_pdf')}")

if __name__ == "__main__":
    main()
