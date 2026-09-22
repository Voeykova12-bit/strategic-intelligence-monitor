from __future__ import annotations

import re

from app.ai.base import AIProvider, NewsAnalysis

INDUSTRY_KEYWORDS = {
    "Automotive": ["автомоб", "авто", "машин", "дилер", "haval", "chery", "geely", "changan", "москвич"],
    "Banking": ["банк", "вклад", "кредит", "карта", "ипотек"],
    "Fintech": ["финтех", "bnpl", "рассроч", "платеж"],
    "Retail": ["ритейл", "магазин", "x5", "магнит", "лента", "вкусвилл"],
    "E-commerce": ["маркетплейс", "e-commerce", "wildberries", "ozon", "онлайн-торгов"],
    "FMCG": ["fmcg", "продукт питания", "напит", "товары повседнев"],
    "Technology": ["искусственн", "нейросет", "ai", "ии", "технолог", "software", "saas"],
    "Telecom": ["телеком", "оператор связи", "мтс", "билайн", "мегафон", "t2"],
    "Pharma": ["фарма", "лекарств", "препарат"],
    "Beauty": ["космет", "beauty", "парфюм"],
    "Real Estate": ["недвижим", "девелоп", "жиль"],
    "Travel": ["туризм", "авиакомпан", "отель", "путешеств"],
}

TOPIC_KEYWORDS = {
    "Advertising": ["реклам", "кампан"],
    "Marketing": ["маркетинг"],
    "Branding": ["бренд", "ребрендинг", "позиционирован"],
    "Product Launch": ["запустил", "запуск", "новый продукт", "новую модель"],
    "Pricing": ["цена", "подорож", "удешев", "скидк"],
    "Promotion": ["промо", "акци"],
    "Consumer Trends": ["потребител", "спрос", "поведен"],
    "Research": ["исследован", "опрос", "аналитик"],
    "Sponsorship": ["спонсор"],
    "Partnership": ["партнер", "партнёр", "коллаборац"],
    "Retail Media": ["retail media", "ритейл медиа"],
    "AI": ["ai", "ии", "искусственн", "нейросет", "генератив"],
    "Martech": ["martech"],
    "Adtech": ["adtech", "programmatic"],
    "M&A": ["m&a", "слияни", "поглощен", "купил компанию", "приобрел"],
    "Investment": ["инвести", "привлек", "раунд"],
    "Financial Results": ["выручк", "прибыл", "ebitda", "финансовые результаты"],
}

BRANDS = ["Сбер", "ВТБ", "Альфа-Банк", "Яндекс", "VK", "Ozon", "Wildberries", "X5", "Магнит", "МТС", "МегаФон", "T2", "Москвич", "Haval", "Chery", "Geely", "Changan", "Jetour", "TENET", "TANK"]


class HeuristicProvider(AIProvider):
    name = "heuristic"

    async def analyze(self, *, title: str, text: str, source: str, published_at: str | None = None) -> NewsAnalysis:
        content = f"{title}\n{text}".lower()
        industries = [k for k, words in INDUSTRY_KEYWORDS.items() if any(w.lower() in content for w in words)] or ["Other"]
        topics = [k for k, words in TOPIC_KEYWORDS.items() if any(w.lower() in content for w in words)]
        brands = [b for b in BRANDS if b.lower() in content]
        score = min(5.0, 1.5 + min(len(topics), 4) * 0.55 + min(len(industries), 2) * 0.3 + min(len(brands), 2) * 0.25)
        clean = re.sub(r"\s+", " ", text or "").strip()
        summary = clean[:450] if clean else title
        return NewsAnalysis(
            relevant=bool(topics or industries != ["Other"]),
            summary=summary,
            strategic_summary=f"Материал относится к {', '.join(industries[:2])} и затрагивает темы: {', '.join(topics[:3]) or 'рыночный контекст'}.",
            why_it_matters="Сигнал может быть полезен для отслеживания активности категории, конкурентов и коммуникационного контекста.",
            implications=["Проверить, формирует ли событие новый паттерн в категории.", "Сопоставить с активностью клиентов и их конкурентами."],
            industries=industries,
            topics=topics,
            brands=brands,
            companies=brands,
            keywords=list(dict.fromkeys((industries + topics + brands)))[:12],
            strategic_relevance_score=round(score, 1),
            novelty_score=2.5,
            confidence_score=0.55,
            event_type=topics[0] if topics else "Market Update",
        )
