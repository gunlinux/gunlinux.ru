from dataclasses import dataclass
from typing import override


@dataclass
class Category:
    id: int | None = None
    title: str = ""
    alias: str = ""
    template: str | None = None
    page: bool | None = False

    @override
    def __str__(self) -> str:
        return f"Category(id={self.id}, title={self.title})"
