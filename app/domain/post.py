import datetime
from dataclasses import dataclass

import markdown

MARKDOWN_EXTENSIONS = ["markdown.extensions.fenced_code"]


@dataclass
class Post:
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
    def markdown(self) -> str:
        return markdown.markdown(self.content or "", extensions=MARKDOWN_EXTENSIONS)

    @property
    def teaser(self) -> str:
        """Short plain-text excerpt (first paragraph, capped) for RSS/meta."""
        first = (self.content or "").strip().split("\n\n", 1)[0].strip()
        if len(first) > 300:
            first = first[:300].rstrip() + "…"
        return first
