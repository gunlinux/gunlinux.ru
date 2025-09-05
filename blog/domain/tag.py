"""Domain models for the Tag entity."""

from dataclasses import dataclass
import typing
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blog.post.models import Post


@dataclass
class Tag:
    """Domain model for blog tag."""

    id: int | None = None
    title: str = ""
    alias: str = ""

    posts: "list[Post] | None" = None

    @typing.override
    def __str__(self):
        return f"{self.title}"
