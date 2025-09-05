"""Domain models for the Post entity."""

from dataclasses import dataclass
import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blog.category.models import Category
    from blog.tags.models import Tag
    from blog.user.models import User


@dataclass
class Post:
    """Domain model for blog post."""

    id: int | None = None
    pagetitle: str = ""
    alias: str = ""
    content: str = ""
    createdon: datetime.datetime | None = None
    publishedon: datetime.datetime | None = None
    category_id: int | None = None
    user_id: int | None = None

    # These would typically be loaded separately in a real implementation
    # to avoid circular dependencies
    user: "User | None" = None
    category: "Category | None" = None
    tags: "list[Tag] | None" = None

    def __post_init__(self):
        if self.createdon is None:
            self.createdon = datetime.datetime.now(datetime.timezone.utc)
        if self.publishedon is None:
            self.publishedon = datetime.datetime.now(datetime.timezone.utc)
