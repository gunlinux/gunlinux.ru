from dataclasses import dataclass
from typing import override


@dataclass
class Tag:
    id: int | None = None
    title: str = ""
    alias: str = ""

    @override
    def __str__(self) -> str:
        return f"{self.title}"
