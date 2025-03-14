# blog/tags/association.py
from sqlalchemy import Column, ForeignKey, Table

from blog.extensions import db

posts_tags = Table(
    "posts_tags",
    db.Model.metadata,
    Column("post_id", ForeignKey("posts.id")),
    Column("tag_id", ForeignKey("tags.id")),
)
