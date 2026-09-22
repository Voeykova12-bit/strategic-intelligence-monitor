from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CollectedItem:
    title: str
    url: str
    published_at: datetime | None = None
    excerpt: str | None = None
    author: str | None = None
    image_url: str | None = None
    raw: dict = field(default_factory=dict)
