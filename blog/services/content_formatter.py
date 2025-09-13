import logging
from blog.domain.post import Post
import markdown


MARKDOWN_EXTENSIONS = ("markdown.extensions.fenced_code",)


logger = logging.getLogger(__name__)

class ContentFormatterError(Exception):
    pass


class ContentFormatter:
    """Service layer for Post entities."""

    def __init__(self, extensions: tuple[str] | None = MARKDOWN_EXTENSIONS):
        self.extensions: tuple[str] | None = extensions

    def markdown_to_html(self, post: str) -> str:
        return markdown.markdown(post or "", extensions=self.extensions)

