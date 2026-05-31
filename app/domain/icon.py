from dataclasses import dataclass
from typing import override


@dataclass
class Icon:
    id: int | None = None
    title: str = ""
    url: str = ""
    content: str | None = None

    @override
    def __str__(self) -> str:
        return f"{self.title}"
