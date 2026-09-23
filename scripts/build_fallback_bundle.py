from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEWS = ROOT / "data" / "news.json"
REPORTS = ROOT / "data" / "reports.json"
METRICS = ROOT / "data" / "metrics.json"
OUT = ROOT / "docs" / "fallback-data.js"

def read(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def main():
    news = read(NEWS, {"items": []})
    reports = read(REPORTS, {"reports": []})
    metrics = read(METRICS, {"metrics": []})

    items = list(news.get("items", []))
    items.sort(key=lambda x: (
        int(x.get("strategic_relevance_score") or round(float(x.get("score", 0) or 0) * 20)),
        x.get("published_at", "")
    ), reverse=True)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "news": {
            "updated_at": news.get("updated_at"),
            "source_count": news.get("source_count"),
            "item_count": min(len(items), 500),
            "categories": news.get("categories", []),
            "items": items[:500],
        },
        "reports": reports,
        "metrics": metrics,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        "window.STRATEGY_RADAR_FALLBACK=" + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    print(f"Built browser fallback bundle with {len(payload['news']['items'])} real items")

if __name__ == "__main__":
    main()
