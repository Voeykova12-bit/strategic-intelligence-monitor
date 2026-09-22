from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import Base, engine


def init_db() -> None:
    settings = get_settings()
    if settings.database_url.startswith("postgresql"):
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
