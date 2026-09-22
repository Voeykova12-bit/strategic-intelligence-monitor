import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncio

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.services.ingestion import ingest_all


async def main():
    init_db()
    with SessionLocal() as db:
        results = await ingest_all(db)
        for row in results:
            print(row)


if __name__ == "__main__":
    asyncio.run(main())
