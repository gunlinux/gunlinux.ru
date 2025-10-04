"""Domain models for the Tag entity."""

from dataclasses import dataclass
from typing import override


@dataclass
class Tag:
    """Domain model for blog tag."""

    id: int | None = None
    title: str = ""
    alias: str = ""

    @override
    def __str__(self):
        return f"{self.title}"
