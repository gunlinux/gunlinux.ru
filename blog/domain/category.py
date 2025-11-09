"""Domain models for the Category entity."""

from dataclasses import dataclass
from typing import override


@dataclass
class Category:
    """Domain model for blog category."""

    id: int | None = None
    title: str = ""
    alias: str = ""
    template: str | None = None
    page: bool | None = False

    @override
    def __str__(self):
        return f"Category(id={self.id}, title={self.title}, template={self.template})"
