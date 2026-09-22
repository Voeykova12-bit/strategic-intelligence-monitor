from app.ai.base import AIProvider
from app.ai.heuristic import HeuristicProvider
from app.ai.openai_provider import OpenAIProvider
from app.core.config import get_settings


def get_ai_provider() -> AIProvider:
    settings = get_settings()
    if settings.ai_provider == "heuristic":
        return HeuristicProvider()
    if settings.ai_provider == "openai":
        return OpenAIProvider()
    if settings.openai_api_key:
        return OpenAIProvider()
    return HeuristicProvider()
