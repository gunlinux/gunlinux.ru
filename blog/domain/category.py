"""Domain models for the Category entity."""

from dataclasses import dataclass
import typing

from blog.post.models import Post


@dataclass
class Category:
    """Domain model for blog category."""

    id: int | None = None
    title: str = ""
    alias: str = ""
    template: str | None = None

    posts: list["Post"] | None = None

    @typing.override
    def __str__(self):
        return f"Category(id={self.id}, title={self.title}, template={self.template})"
