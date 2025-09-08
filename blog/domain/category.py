"""Domain models for the Category entity."""

from dataclasses import dataclass
import typing
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blog.domain.post import Post as PostDomain


@dataclass
class Category:
    """Domain model for blog category."""

    id: int | None = None
    title: str = ""
    alias: str = ""
    template: str | None = None

    posts: "list[PostDomain] | None" = None

    @typing.override
    def __str__(self):
        return f"Category(id={self.id}, title={self.title}, template={self.template})"
