import pytest
import os
import sqlalchemy as sa

from blog import create_app
from blog.extensions import db
from blog.post.models import Post
from blog.category.models import Category


@pytest.fixture()
def test_client():
    os.environ["FLASK_ENV"] = "testing"
    app = create_app()
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            page_category = Category(id=1, title="page", alias="page")  # type: ignore
            db.session.add(page_category)
            db.session.commit()
            yield client
        with app.app_context():
            db.session.remove()
            db.drop_all()


def post_helper(prefix="post", page=False):
    post = Post()
    post.pagetitle = f"{prefix}_title"
    post.alias = f"{prefix}_alias"
    post.content = f"{prefix}_content"
    if page:
        post.category_id = 1
    return post


def test_post(test_client):
    with test_client.application.app_context():
        post = post_helper(page=False)
        db.session.add(post)
        db.session.commit()
    rv = test_client.get("/post_alias")
    assert rv.status == "200 OK"
    assert b"post_content" in rv.data
    assert b"post_title" in rv.data


def test_page(test_client):
    with test_client.application.app_context():
        testpage = post_helper(prefix="page", page=True)
        db.session.add(testpage)
        db.session.commit()
    rv = test_client.get("/page_alias")
    assert rv.status == "200 OK"
    assert b"page_content" in rv.data
    assert b"page_title" in rv.data


def test_post_index(test_client):
    with test_client.application.app_context():
        post = post_helper()
        db.session.add(post)
        db.session.commit()
    rv = test_client.get("/")
    assert rv.status == "200 OK"
    assert b"post_title" in rv.data


def test_page_index(test_client):
    with test_client.application.app_context():
        testpage = post_helper(prefix="page", page=True)
        db.session.add(testpage)
        db.session.commit()
    rv = test_client.get("/")
    assert rv.status == "200 OK"

    with test_client.application.app_context():
        post_query = sa.select(Post).where(
            Post.publishedon.isnot(None),
            Post.alias == "page_alias",
        )
        post = db.first_or_404(post_query)
        assert post.category_id == 1
    assert b"page_alias" in rv.data
