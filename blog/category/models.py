"""SqlAlchemy models."""
from typing import List, TYPE_CHECKING

from sqlalchemy.orm import Mapped, relationship

from blog.extensions import db
if TYPE_CHECKING:
    from blog.post.models import Post


class Category(db.Model):
    """orm model for blog post."""

    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), default='')
    alias = db.Column(db.String(255), unique=True, nullable=False)
    posts: Mapped[List["Post"]] = relationship()

    def __init__(self, title, alias):
        self.title = title
        self.alias = alias

    def __str__(self):
        return f'{self.title}'
