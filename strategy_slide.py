from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Strategic Intelligence Monitor")
    environment: str = os.getenv("ENVIRONMENT", "development")
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./strategic_intelligence.db")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    app_timezone: str = os.getenv("APP_TIMEZONE", "Europe/Moscow")
    digest_hour_local: int = int(os.getenv("DIGEST_HOUR_LOCAL", "8"))
    collector_interval_minutes: int = int(os.getenv("COLLECTOR_INTERVAL_MINUTES", "30"))
    source_config_path: str = os.getenv("SOURCE_CONFIG_PATH", "config/sources.yaml")
    client_config_path: str = os.getenv("CLIENT_CONFIG_PATH", "config/clients.yaml")
    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "20"))
    user_agent: str = os.getenv("USER_AGENT", "StrategicIntelligenceMonitor/0.1 (+internal agency research)")
    respect_robots: bool = _bool("RESPECT_ROBOTS", True)
    max_articles_per_source: int = int(os.getenv("MAX_ARTICLES_PER_SOURCE", "30"))
    min_relevance_before_llm: float = float(os.getenv("MIN_RELEVANCE_BEFORE_LLM", "0.20"))
    ai_provider: str = os.getenv("AI_PROVIDER", "auto")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.6-terra")
    openai_embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    daily_ai_budget_usd: float = float(os.getenv("DAILY_AI_BUDGET_USD", "10"))
    ai_budget_reserve_usd: float = float(os.getenv("AI_BUDGET_RESERVE_USD", "0.05"))
    telegram_bot_token: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str | None = os.getenv("TELEGRAM_CHAT_ID")
    dashboard_api_url: str = os.getenv("DASHBOARD_API_URL", "http://api:8000")

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
