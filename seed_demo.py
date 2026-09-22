from __future__ import annotations

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.db.models import Article
from app.services.analytics import signals


def build_morning_digest(db: Session, hours: int = 24) -> str:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    articles = (
        db.query(Article)
        .filter(Article.collected_at >= since)
        .order_by(Article.strategic_relevance_score.desc(), Article.published_at.desc())
        .limit(40)
        .all()
    )
    top = articles[:15]
    sigs = signals(db, days=7, min_articles=2, limit=5)
    lines = ["# STRATEGIC MORNING BRIEF", "", "## TOP SIGNALS"]
    if sigs:
        for s in sigs:
            lines.append(f"- **{s['title']}** — {s['description']} {s['strategic_implication']}")
    else:
        lines.append("- Пока недостаточно данных для устойчивых сигналов.")
    lines += ["", "## TOP NEWS"]
    for i, a in enumerate(top, 1):
        lines += [
            f"### {i}. {a.title}",
            f"**Что произошло:** {a.summary or a.excerpt or 'Краткое описание пока не сформировано.'}",
            f"**Почему важно:** {a.why_it_matters or a.strategic_summary or 'Требуется дополнительный анализ.'}",
            f"**Strategic implication:** {(a.implications or ['Отслеживать развитие сюжета.'])[0]}",
            f"**Score:** {a.strategic_relevance_score}/5 · **Источник:** {a.source_name or a.source_domain} · {a.url}",
            "",
        ]
    lines += ["## WATCHLIST"]
    watch = [a for a in articles if a.strategic_relevance_score >= 4][:5]
    lines.extend([f"- {a.title}" for a in watch] or ["- Нет сюжетов с score ≥ 4 за выбранный период."])
    return "\n".join(lines)
