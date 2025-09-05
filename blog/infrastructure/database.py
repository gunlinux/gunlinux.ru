"""SQLAlchemy Table Definitions (Infrastructure).

This module contains the SQLAlchemy table definitions
following the UNION Architecture pattern where infrastructure
is separated from domain models.
"""

from sqlalchemy import Table, Column, Integer, String, Text, DateTime, ForeignKey


# Table definitions (Infrastructure layer)
def get_users_table(metadata):
    return Table(
        "users",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(50), nullable=False),
        Column("password", String(255)),  # Adjusted length for password hashes
        Column("authenticated", Integer, default=0),  # Using Integer for boolean
        Column("createdon", DateTime(timezone=True)),
        extend_existing=True,
    )


def get_posts_table(metadata):
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


def get_categories_table(metadata):
    return Table(
        "categories",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("title", String(255)),
        Column("alias", String(255), unique=True),
        Column("template", String(255), nullable=True),
        extend_existing=True,
    )


def get_tags_table(metadata):
    return Table(
        "tags",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("title", String(255)),
        Column("alias", String(255), unique=True),
        extend_existing=True,
    )


def get_posts_tags_table(metadata):
    return Table(
        "posts_tags",
        metadata,
        Column("post_id", Integer, ForeignKey("posts.id")),
        Column("tag_id", Integer, ForeignKey("tags.id")),
        extend_existing=True,
    )
