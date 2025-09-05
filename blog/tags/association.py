# blog/tags/association.py
from sqlalchemy import Column, ForeignKey, Table

# This file is now deprecated as we're using the posts_tags_table from infrastructure.database
# Keeping it for backward compatibility, but it should be removed in future versions
from blog.extensions import db

posts_tags = Table(
    "posts_tags",
    db.Model.metadata,
    Column("post_id", ForeignKey("posts.id")),
    Column("tag_id", ForeignKey("tags.id")),
)
