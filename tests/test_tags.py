import pytest
import os
import datetime

from blog import create_app
from blog.extensions import db
from blog.domain.post import Post as PostDomain
from blog.domain.tag import Tag as TagDomain
from blog.services.factory import ServiceFactory
from blog.post.models import Post as PostORM
from blog.tags.models import Tag as TagORM


@pytest.fixture()
def test_client():
    os.environ["FLASK_ENV"] = "testing"
    app = create_app()
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.session.remove()
            db.drop_all()


def test_get_posts_by_tag(test_client):
    with test_client.application.app_context():
        # Use service layer to create domain models
        tag_service = ServiceFactory.create_tag_service()
        post_service = ServiceFactory.create_post_service()

        # Create a tag using domain model
        tag_domain = TagDomain(title="test-tag", alias="test-tag")
        tag = tag_service.create_tag(tag_domain)

        # Create posts using domain models
        post1_domain = PostDomain(
            pagetitle="Post 1",
            alias="post-1",
            content="Content 1",
            publishedon=datetime.datetime.now(datetime.timezone.utc),
        )
        post1 = post_service.create_post(post1_domain)

        post2_domain = PostDomain(
            pagetitle="Post 2",
            alias="post-2",
            content="Content 2",
            publishedon=datetime.datetime.now(datetime.timezone.utc),
        )
        post2 = post_service.create_post(post2_domain)

        post3_domain = PostDomain(
            pagetitle="Post 3",
            alias="post-3",
            content="Content 3",
            publishedon=datetime.datetime.now(datetime.timezone.utc),
        )
        post_service.create_post(post3_domain)

        # Manually create the tag-post relationships at the ORM level
        # This is a workaround for the current limitation in the domain model approach
        tag_orm = db.session.get(TagORM, tag.id)
        post1_orm = db.session.get(PostORM, post1.id)
        post2_orm = db.session.get(PostORM, post2.id)

        if tag_orm and post1_orm and post2_orm:
            post1_orm.tags.append(tag_orm)
            post2_orm.tags.append(tag_orm)
            db.session.commit()

    response = test_client.get("/tags/test-tag")
    assert response.status_code == 200

    assert b"Post 1" in response.data
    assert b"Post 2" in response.data
    assert b"Post 3" not in response.data


def test_post_have_tag(test_client):
    with test_client.application.app_context():
        # Use service layer to create domain models
        tag_service = ServiceFactory.create_tag_service()
        post_service = ServiceFactory.create_post_service()

        # Create tags using domain models
        tag1_domain = TagDomain(title="test-tag1", alias="test-tag1")
        tag1 = tag_service.create_tag(tag1_domain)

        tag2_domain = TagDomain(title="test-tag2", alias="test-tag2")
        tag_service.create_tag(tag2_domain)

        # Create a post
        post1_domain = PostDomain(
            pagetitle="Post 1",
            alias="post-1",
            content="Content 1",
            publishedon=datetime.datetime.now(datetime.timezone.utc),
        )
        post1 = post_service.create_post(post1_domain)

        # Manually create the tag-post relationship at the ORM level
        # This is a workaround for the current limitation in the domain model approach
        tag1_orm = db.session.get(TagORM, tag1.id)
        post1_orm = db.session.get(PostORM, post1.id)

        if tag1_orm and post1_orm:
            post1_orm.tags.append(tag1_orm)
            db.session.commit()

    response = test_client.get("/post-1")
    assert response.status_code == 200

    assert b"test-tag1" in response.data
    assert b"test-tag2" not in response.data
