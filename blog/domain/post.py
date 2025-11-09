"""Domain models for the Post entity."""

from dataclasses import dataclass
import datetime
import markdown


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
    is_page: bool = False
    user_id: int | None = None

    def __post_init__(self):
        if self.createdon is None:
            self.createdon = datetime.datetime.now(datetime.timezone.utc)

    @property
    def markdown(self):
        return markdown.markdown(self.content or "", extensions=MARKDOWN_EXTENSIONS)
