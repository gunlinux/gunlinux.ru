"""Domain models for the User entity."""

import datetime
import typing
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blog.domain.post import Post as PostDomain

    Post = PostDomain
else:
    Post = "Post"


@dataclass
class User:
    """Domain model for user."""

    id: int | None = None
    name: str = ""
    password: str = ""
    authenticated: bool = False
    createdon: datetime.datetime | None = None
    posts: list[Post] | None = None

    def __post_init__(self):
        if self.createdon is None:
            self.createdon = datetime.datetime.now(datetime.timezone.utc)

    @typing.override
    def __str__(self):
        return f"{self.name}"
