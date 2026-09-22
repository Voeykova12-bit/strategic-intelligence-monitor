from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import Article
from app.services.analytics import signals, trends
from app.services.digest import build_morning_digest
from app.services.search import keyword_search


def handle_command(db: Session, text: str) -> str:
    text = (text or "").strip()
    command, _, arg = text.partition(" ")
    command = command.split("@", 1)[0].lower()
    arg = arg.strip()

    if command == "/today":
        return build_morning_digest(db, hours=24)[:12000]
    if command == "/search":
        if not arg:
            return "Использование: /search запрос"
        rows = keyword_search(db, arg, 8)
        return "\n\n".join(f"• {a.title}\nScore {a.strategic_relevance_score}/5\n{a.url}" for a in rows) or "Ничего не найдено."
    if command == "/signals":
        rows = signals(db, days=30, limit=8)
        return "\n\n".join(f"• {s['title']}\n{s['description']}\n{s['strategic_implication']}" for s in rows) or "Пока недостаточно данных для сигналов."
    if command == "/trends":
        data = trends(db, days=30, limit=10)
        return "TOPICS\n" + "\n".join(f"• {name}: {count}" for name, count in data["topics"])
    if command == "/industry":
        if not arg:
            return "Использование: /industry Automotive"
        rows = db.query(Article).order_by(Article.strategic_relevance_score.desc()).limit(500).all()
        rows = [a for a in rows if arg.lower() in {str(i).lower() for i in (a.industries or [])}][:8]
        return "\n\n".join(f"• {a.title}\n{a.url}" for a in rows) or "Нет материалов по этой категории."
    if command == "/client":
        if not arg:
            return "Использование: /client moskvich"
        rows = db.query(Article).order_by(Article.strategic_relevance_score.desc()).limit(1000).all()
        rows = [a for a in rows if arg.lower() in {str(k).lower() for k in (a.client_matches or {}).keys()}][:8]
        return "\n\n".join(f"• {a.title}\n{a.url}" for a in rows) or "Нет материалов по этому клиенту."
    return "Команды: /today, /search, /signals, /trends, /industry, /client"
