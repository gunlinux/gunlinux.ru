"""Domain models for the Category entity."""

from dataclasses import dataclass
import typing
from typing import TYPE_CHECKING, Optional, List

if TYPE_CHECKING:
    from blog.domain.post import Post as PostDomain


@dataclass
class Category:
    """Domain model for blog category."""

    id: Optional[int] = None
    title: str = ""
    alias: str = ""
    template: Optional[str] = None

    posts: "Optional[List[PostDomain]]" = None

    @typing.override
    def __str__(self):
        return f"Category(id={self.id}, title={self.title}, template={self.template})"
