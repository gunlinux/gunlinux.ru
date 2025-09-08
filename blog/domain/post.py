"""Domain models for the Post entity."""

from dataclasses import dataclass
import datetime
import markdown
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blog.domain.category import Category as CategoryDomain
    from blog.domain.tag import Tag as TagDomain
    from blog.domain.user import User as UserDomain


MARKDOWN_EXTENSIONS = ["markdown.extensions.fenced_code"]


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
    user: "UserDomain | None" = None
    category: "CategoryDomain | None" = None
    tags: "list[TagDomain] | None" = None

    def __post_init__(self):
        if self.createdon is None:
            self.createdon = datetime.datetime.now(datetime.timezone.utc)
        # Don't set default for publishedon - it should be None for unpublished posts

    @property
    def markdown(self):
        return markdown.markdown(self.content or "", extensions=MARKDOWN_EXTENSIONS)
