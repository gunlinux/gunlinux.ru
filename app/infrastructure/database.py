"""SQLAlchemy Table Definitions (Infrastructure layer)."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.sql.schema import MetaData


def get_users_table(metadata: MetaData) -> Table:
    return Table(
        "users",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(50), nullable=False),
        Column("password", String(255)),
        Column("authenticated", Integer, default=0),
        Column("createdon", DateTime(timezone=True)),
        extend_existing=True,
    )


def get_posts_table(metadata: MetaData) -> Table:
    return Table(
        "posts",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("pagetitle", String(255), nullable=False),
        Column("alias", String(255), nullable=False, unique=True),
        Column("content", Text),
        Column("createdon", DateTime(timezone=True)),
        Column("publishedon", DateTime(timezone=True)),
        Column("category_id", Integer, ForeignKey("categories.id"), nullable=True),
        Column("user_id", Integer, ForeignKey("users.id"), nullable=True),
        extend_existing=True,
    )


def get_categories_table(metadata: MetaData) -> Table:
    return Table(
        "categories",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("title", String(255)),
        Column("alias", String(255), unique=True),
        Column("template", String(255), nullable=True),
        Column("page", Boolean(), nullable=True, default=False),
        extend_existing=True,
    )


def get_tags_table(metadata: MetaData) -> Table:
    return Table(
        "tags",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("title", String(255)),
        Column("alias", String(255), unique=True),
        extend_existing=True,
    )


def get_posts_tags_table(metadata: MetaData) -> Table:
    return Table(
        "posts_tags",
        metadata,
        Column("post_id", Integer, ForeignKey("posts.id")),
        Column("tag_id", Integer, ForeignKey("tags.id")),
        extend_existing=True,
    )


def get_icons_table(metadata: MetaData) -> Table:
    return Table(
        "icons",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("title", String(255), nullable=False, unique=True),
        Column("url", String(255), nullable=False, unique=True),
        Column("content", Text),
        extend_existing=True,
    )
