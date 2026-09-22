from __future__ import annotations

import httpx

from app.core.config import get_settings


async def send_telegram(text: str) -> bool:
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return False
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    chunks = [text[i:i + 3900] for i in range(0, len(text), 3900)]
    async with httpx.AsyncClient(timeout=20) as client:
        for chunk in chunks:
            res = await client.post(url, json={"chat_id": settings.telegram_chat_id, "text": chunk, "disable_web_page_preview": True})
            res.raise_for_status()
    return True
