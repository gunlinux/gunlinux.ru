"""Integration tests for the full request lifecycle."""

import pytest
import os
import datetime

from blog import create_app
from blog.extensions import db
from blog.domain.post import Post as PostDomain
from blog.domain.category import Category as CategoryDomain
from blog.domain.tag import Tag as TagDomain
from blog.domain.user import User as UserDomain
from blog.services.factory import ServiceFactory


@pytest.fixture()
def integration_client():
    """Create a test client for the Flask app with full test data."""
    os.environ["FLASK_ENV"] = "testing"
    app = create_app()
    with app.test_client() as client:
        with app.app_context():
            db.create_all()

            # Create test data using services (to ensure proper layer interaction)
            category_service = ServiceFactory.create_category_service()
            user_service = ServiceFactory.create_user_service()
            post_service = ServiceFactory.create_post_service()
            tag_service = ServiceFactory.create_tag_service()

            # Create a user
            user = UserDomain(name="testuser", password="testpassword")
            created_user = user_service.create_user(user)

            # Create categories
            page_category = CategoryDomain(title="page", alias="page", page=True)
            created_page_category = category_service.create_category(page_category)

            regular_category = CategoryDomain(title="tech", alias="tech")
            created_regular_category = category_service.create_category(
                regular_category
            )

            # Create tags
            tag1 = TagDomain(title="python", alias="python")
            created_tag1 = tag_service.create_tag(tag1)

            tag2 = TagDomain(title="flask", alias="flask")
            created_tag2 = tag_service.create_tag(tag2)

            # Create posts
            # Regular published post
            post1 = PostDomain(
                pagetitle="Test Post 1",
                alias="test-post-1",
                content="This is test post 1 content",
                publishedon=datetime.datetime.now(datetime.timezone.utc),
                user_id=created_user.id,
                category_id=None,
            )
            created_post1 = post_service.create_post(post1)

            # Page
            post2 = PostDomain(
                pagetitle="Test Page",
                alias="test-page",
                content="This is a test page content",
                publishedon=None,
                user_id=created_user.id,
                category_id=created_page_category.id,
            )
            created_post2 = post_service.create_post(post2)

            # Post with tags (manually create the tag-post relationship at the ORM level)
            # This is a workaround for the current limitation in the domain model approach
            from blog.post.models import Post as PostORM
            from blog.tags.models import Tag as TagORM

            post3_orm = db.session.get(PostORM, created_post1.id)
            tag1_orm = db.session.get(TagORM, created_tag1.id)
            tag2_orm = db.session.get(TagORM, created_tag2.id)

            if post3_orm and tag1_orm and tag2_orm:
                post3_orm.tags.append(tag1_orm)
                post3_orm.tags.append(tag2_orm)
                db.session.commit()

            yield (
                client,
                {
                    "user": created_user,
                    "page_category": created_page_category,
                    "regular_category": created_regular_category,
                    "tags": [created_tag1, created_tag2],
                    "posts": [created_post1, created_post2],
                },
            )

        with app.app_context():
            db.session.remove()
            db.drop_all()


def test_full_post_lifecycle(integration_client):
    """Test the full lifecycle of creating and viewing a post."""
    client, test_data = integration_client

    # Test that the post is accessible through the web interface
    post = test_data["posts"][0]
    response = client.get(f"/{post.alias}")
    assert response.status_code == 200
    assert post.pagetitle.encode() in response.data
    assert post.content.encode() in response.data


def test_full_page_lifecycle(integration_client):
    """Test the full lifecycle of creating and viewing a page."""
    client, test_data = integration_client

    # Test that the page is accessible through the web interface
    page = test_data["posts"][1]
    response = client.get(f"/{page.alias}")
    assert response.status_code == 200
    assert page.pagetitle.encode() in response.data
    assert page.content.encode() in response.data


def test_post_with_tags(integration_client):
    """Test that posts with tags are displayed correctly."""
    client, test_data = integration_client

    # Test that the post with tags is accessible
    post = test_data["posts"][0]
    response = client.get(f"/{post.alias}")
    assert response.status_code == 200

    # Check that tags are displayed
    for tag in test_data["tags"]:
        assert tag.title.encode() in response.data


def test_tags_page(integration_client):
    """Test that the tags page displays tags correctly."""
    client, test_data = integration_client

    # Test that the tags index page shows tags
    response = client.get("/tags/")
    assert response.status_code == 200

    # Check that tags are displayed
    for tag in test_data["tags"]:
        assert tag.title.encode() in response.data


def test_individual_tag_page(integration_client):
    """Test that individual tag pages work correctly."""
    client, test_data = integration_client

    # Test that individual tag pages work
    tag = test_data["tags"][0]
    response = client.get(f"/tags/{tag.alias}?hx=True")
    assert response.status_code == 200
    assert tag.title.encode() in response.data


def test_rss_feed(integration_client):
    """Test that the RSS feed works correctly."""
    client, test_data = integration_client

    # Test that the RSS feed works
    response = client.get("/rss.xml")
    assert response.status_code == 200
    assert response.content_type == "application/rss+xml"

    # Check that published posts are in the feed
    # Only the first post is published (has publishedon set)
    published_post = test_data["posts"][0]
    assert published_post.pagetitle.encode() in response.data


def test_domain_model_consistency(integration_client):
    """Test that domain models are properly passed between layers."""
    client, test_data = integration_client

    # Test that we can retrieve the same data through services
    post_service = ServiceFactory.create_post_service()
    category_service = ServiceFactory.create_category_service()
    tag_service = ServiceFactory.create_tag_service()
    user_service = ServiceFactory.create_user_service()

    # Check post data consistency
    original_post = test_data["posts"][0]
    retrieved_post = post_service.get_post_by_id(original_post.id)
    assert retrieved_post is not None
    assert retrieved_post.pagetitle == original_post.pagetitle
    assert retrieved_post.alias == original_post.alias
    assert retrieved_post.content == original_post.content

    # Check user data consistency
    original_user = test_data["user"]
    retrieved_user = user_service.get_user_by_id(original_user.id)
    assert retrieved_user is not None
    assert retrieved_user.name == original_user.name

    # Check category data consistency
    original_category = test_data["page_category"]
    retrieved_category = category_service.get_category_by_id(original_category.id)
    assert retrieved_category is not None
    assert retrieved_category.title == original_category.title
    assert retrieved_category.alias == original_category.alias

    # Check tag data consistency
    original_tag = test_data["tags"][0]
    retrieved_tag = tag_service.get_tag_by_id(original_tag.id)
    assert retrieved_tag is not None
    assert retrieved_tag.title == original_tag.title
    assert retrieved_tag.alias == original_tag.alias
