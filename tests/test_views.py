"""Integration tests for view functions using domain models."""

import pytest
import os
import datetime

from blog import create_app
from blog.extensions import db
from blog.domain.post import Post as PostDomain
from blog.domain.category import Category as CategoryDomain
from blog.domain.tag import Tag as TagDomain
from blog.services.factory import ServiceFactory


@pytest.fixture()
def test_client():
    """Create a test client for the Flask app."""
    os.environ["FLASK_ENV"] = "testing"
    app = create_app()
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Create a page category for testing
            category_service = ServiceFactory.create_category_service()
            page_category = CategoryDomain(id=1, title="page", alias="page")
            category_service.create_category(page_category)
            yield client
        with app.app_context():
            db.session.remove()
            db.drop_all()


def create_test_post(
    title="Test Post", alias="test-post", content="Test content", page=False
):
    """Helper function to create a test post."""
    post_service = ServiceFactory.create_post_service()
    post = PostDomain(
        pagetitle=title,
        alias=alias,
        content=content,
        createdon=datetime.datetime.now(datetime.timezone.utc),
        publishedon=datetime.datetime.now(datetime.timezone.utc) if not page else None,
        category_id=1 if page else None,
    )
    return post_service.create_post(post)


def create_test_tag(title="Test Tag", alias="test-tag"):
    """Helper function to create a test tag."""
    tag_service = ServiceFactory.create_tag_service()
    tag = TagDomain(
        title=title,
        alias=alias,
    )
    return tag_service.create_tag(tag)


def test_post_view(test_client):
    """Test that post view works with domain models."""
    # Create a test post
    post = create_test_post()

    # Request the post page
    response = test_client.get(f"/{post.alias}")
    assert response.status_code == 200
    assert post.pagetitle.encode() in response.data
    assert post.content.encode() in response.data


def test_page_view(test_client):
    """Test that page view works with domain models."""
    # Create a test page
    page = create_test_post(
        title="Test Page", alias="test-page", content="Page content", page=True
    )

    # Request the page
    response = test_client.get(f"/{page.alias}")
    assert response.status_code == 200
    assert page.pagetitle.encode() in response.data
    assert page.content.encode() in response.data


def test_index_view(test_client):
    """Test that index view works with domain models."""
    # Create a test post
    post = create_test_post()

    # Request the index page
    response = test_client.get("/")
    assert response.status_code == 200
    assert post.pagetitle.encode() in response.data


def test_tag_index_view(test_client):
    """Test that tag index view works with domain models."""
    # Create a test tag
    tag = create_test_tag()

    # Request the tags index page
    response = test_client.get("/tags/")
    assert response.status_code == 200
    assert tag.title.encode() in response.data


def test_tag_view(test_client):
    """Test that tag view works with domain models."""
    # Create a test tag
    tag = create_test_tag()

    # Request the tag page
    response = test_client.get(f"/tags/{tag.alias}")
    assert response.status_code == 200
    assert tag.title.encode() in response.data


def test_404_view(test_client):
    """Test that 404 view works correctly."""
    # Request a non-existent page
    response = test_client.get("/non-existent-page")
    assert response.status_code == 404


def test_rss_view(test_client):
    """Test that RSS view works with domain models."""
    # Create a test post
    post = create_test_post()

    # Request the RSS feed
    response = test_client.get("/rss.xml")
    assert response.status_code == 200
    assert response.content_type == "application/rss+xml"
    assert post.pagetitle.encode() in response.data


def test_robots_view(test_client):
    """Test that robots.txt view works."""
    # Request the robots.txt file
    response = test_client.get("/robots.txt")
    assert response.status_code == 200
    assert b"User-agent: *" in response.data


def test_markdown_view(test_client):
    """Test that markdown conversion works."""
    # Post markdown data
    response = test_client.post("/md/", data={"data": "# Test Header"})
    assert response.status_code == 200
    assert b"<h1>Test Header</h1>" in response.data
