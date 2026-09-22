import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import datetime, timedelta, timezone

from app.db.init_db import init_db
from app.db.models import Article, Source, StoryCluster
from app.db.session import SessionLocal

DEMO = [
    ("Retail media: маркетплейсы расширяют рекламные инструменты", "Retail", "Retail Media", 4.2),
    ("Банки усиливают продвижение накопительных продуктов", "Banking", "Product Launch", 4.0),
    ("Автобренды расширяют спортивные партнерства", "Automotive", "Sponsorship", 3.8),
    ("Компании внедряют генеративный ИИ в маркетинговые процессы", "Technology", "AI", 4.4),
    ("Ритейлеры развивают персонализированные промо", "Retail", "Promotion", 3.6),
]


def main():
    init_db()
    with SessionLocal() as db:
        source = db.query(Source).filter_by(name="Demo Research Feed").one_or_none()
        if not source:
            source = Source(name="Demo Research Feed", source_type="demo", url="https://example.com", country="RU", language="ru", reliability_score=4.2, priority=4, topics=["business", "marketing"])
            db.add(source); db.flush()
        for idx, (title, industry, topic, score) in enumerate(DEMO):
            url = f"https://example.com/demo/{idx}"
            if db.query(Article).filter_by(canonical_url=url).first():
                continue
            dt = datetime.now(timezone.utc) - timedelta(hours=idx * 4)
            cluster = StoryCluster(title=title, earliest_publication=dt, latest_update=dt)
            db.add(cluster); db.flush()
            article = Article(
                source_id=source.id, cluster_id=cluster.id, title=title, original_title=title, url=url, canonical_url=url,
                source_name=source.name, source_domain="example.com", published_at=dt, language="ru", country="RU", market_scope="Russia",
                full_text=title, excerpt=title, summary=f"Демо-материал: {title}.",
                strategic_summary=f"Сигнал по категории {industry}: тема {topic} набирает значение для коммуникационной стратегии.",
                why_it_matters="Материал показывает изменение конкурентного или коммуникационного контекста категории.",
                implications=["Проверить реакцию лидеров категории.", "Учесть сигнал при следующем обновлении стратегии."],
                industries=[industry], topics=[topic], strategic_relevance_score=score, novelty_score=3.5,
                source_quality_score=4.2, confidence_score=0.8, keywords=[industry, topic],
            )
            db.add(article); db.flush(); cluster.primary_article_id = article.id
        db.commit()
    print("Demo data loaded")


if __name__ == "__main__":
    main()
