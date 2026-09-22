from __future__ import annotations

import re

HIGH_VALUE_TERMS = {
    "реклама", "маркетинг", "бренд", "кампания", "рынок", "продажи", "доля рынка", "запуск", "новый продукт",
    "инвестиции", "сделка", "партнерство", "партнёрство", "спонсорство", "исследование", "аудитория", "потребител",
    "ритейл", "банк", "финтех", "маркетплейс", "автомоб", "fmcg", "телеком", "фарма", "ai", "ии", "adtech", "martech",
    "retail media", "e-commerce", "ecommerce", "медиапотребление", "ребрендинг", "позиционирование", "цены", "промо",
}


def relevance_prefilter(title: str, excerpt: str | None = None, source_topics: list[str] | None = None) -> float:
    text = f"{title} {excerpt or ''}".lower()
    hits = sum(1 for term in HIGH_VALUE_TERMS if term in text)
    topical_bonus = min(len(source_topics or []) * 0.03, 0.18)
    number_bonus = 0.05 if re.search(r"\b\d+(?:[.,]\d+)?%", text) else 0.0
    return min(1.0, hits * 0.14 + topical_bonus + number_bonus)
