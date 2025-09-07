"""Domain models for the Post entity."""

from dataclasses import dataclass
import datetime
import markdown
from typing import TYPE_CHECKING, Optional, List

if TYPE_CHECKING:
    from blog.domain.category import Category as CategoryDomain
    from blog.domain.tag import Tag as TagDomain
    from blog.domain.user import User as UserDomain


MARKDOWN_EXTENSIONS = ["markdown.extensions.fenced_code"]


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
    user: "Optional[UserDomain]" = None
    category: "Optional[CategoryDomain]" = None
    tags: "Optional[List[TagDomain]]" = None

    def __post_init__(self):
        if self.createdon is None:
            self.createdon = datetime.datetime.now(datetime.timezone.utc)
        # Don't set default for publishedon - it should be None for unpublished posts

    @property
    def markdown(self):
        return markdown.markdown(self.content or "", extensions=MARKDOWN_EXTENSIONS)
