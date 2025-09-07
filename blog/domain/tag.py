"""Domain models for the Tag entity."""

from dataclasses import dataclass
import typing
from typing import TYPE_CHECKING, Optional, List

if TYPE_CHECKING:
    from blog.domain.post import Post as PostDomain


@dataclass
class Tag:
    """Domain model for blog tag."""

    id: Optional[int] = None
    title: str = ""
    alias: str = ""

    posts: "Optional[List[PostDomain]]" = None

    @typing.override
    def __str__(self):
        return f"{self.title}"
