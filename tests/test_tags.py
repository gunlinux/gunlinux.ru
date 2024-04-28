import pytest
import os

from blog import create_app
from blog import db
from blog.post.models import Post
from blog.tags.models import Tag


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
        tag = Tag(title='test-tag', alias='test-tag')
        db.session.add(tag)

        post1 = Post(pagetitle='Post 1', alias='post-1', content='Content 1')
        post1.tags.append(tag)

        post2 = Post(pagetitle='Post 2', alias='post-2', content='Content 2')
        post2.tags.append(tag)

        post3 = Post(pagetitle='Post 3', alias='post-3', content='Content 3')

        db.session.add(post1)
        db.session.add(post2)
        db.session.add(post3)
        db.session.commit()

    response = test_client.get('/tags/test-tag')
    assert response.status_code == 200

    assert b'Post 1' in response.data
    assert b'Post 2' in response.data
    assert b'Post 3' not in response.data


def test_post_have_tag(test_client):
    with test_client.application.app_context():
        tag1 = Tag(title='test-tag1', alias='test-tag1')
        db.session.add(tag1)
        tag2 = Tag(title='test-tag2', alias='test-tag2')
        db.session.add(tag2)

        post1 = Post(pagetitle='Post 1', alias='post-1', content='Content 1')
        post1.tags.append(tag1)

        db.session.add(post1)
        db.session.commit()

    response = test_client.get('/post-1')
    assert response.status_code == 200

    assert b'test-tag1' in response.data
    assert b'test-tag2' not in response.data
