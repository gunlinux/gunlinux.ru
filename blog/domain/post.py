"""Domain models for the Post entity."""

from dataclasses import dataclass
from typing import Optional, List
import datetime

from blog.category.models import Category
from blog.tags.models import Tag
from blog.user.models import User


@dataclass
class Post:
    """Domain model for blog post."""

    id: Optional[int] = None
    pagetitle: str = ""
    alias: str = ""
    content: str = ""
    createdon: Optional[datetime.datetime] = None
    publishedon: Optional[datetime.datetime] = None
    category_id: Optional[int] = None
    user_id: Optional[int] = None

    # These would typically be loaded separately in a real implementation
    # to avoid circular dependencies
    user: Optional[User] = None
    category: Optional[Category] = None
    tags: Optional[List[Tag]] = None

    def __post_init__(self):
        if self.createdon is None:
            self.createdon = datetime.datetime.now(datetime.timezone.utc)
        if self.publishedon is None:
            self.publishedon = datetime.datetime.now(datetime.timezone.utc)
