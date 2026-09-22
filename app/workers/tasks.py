import asyncio

from app.db.session import SessionLocal
from app.services.digest import build_morning_digest
from app.services.ingestion import ingest_all
from app.telegram.bot import send_telegram
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.collect_news")
def collect_news():
    with SessionLocal() as db:
        return asyncio.run(ingest_all(db))


@celery_app.task(name="app.workers.tasks.send_morning_digest")
def send_morning_digest():
    with SessionLocal() as db:
        digest = build_morning_digest(db)
    return asyncio.run(send_telegram(digest))
