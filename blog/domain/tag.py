"""Domain models for the Tag entity."""

from dataclasses import dataclass
import typing


@dataclass
class Tag:
    """Domain model for blog tag."""

    id: int | None = None
    title: str = ""
    alias: str = ""

    @typing.override
    def __str__(self):
        return f"{self.title}"
