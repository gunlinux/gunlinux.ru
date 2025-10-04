"""Domain models for the Icon entity."""

from typing import override
from dataclasses import dataclass


@dataclass
class Icon:
    """Domain model for blog icon."""

    id: int | None = None
    title: str = ""
    url: str = ""
    content: str | None = None

    @override
    def __str__(self):
        return f"Icon(id={self.id}, title={self.title})"
