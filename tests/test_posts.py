import pytest
import os

from blog import create_app
from blog import db
from blog.post.models import Post


@pytest.fixture(scope='module')
def test_client():
    os.environ['FLASK_ENV'] = 'testing'
    app = create_app()
    db.init_app(app)
    testing_client = app.test_client()
    ctx = app.app_context()
    ctx.push()
    db.create_all()
    yield testing_client
    db.drop_all()
    ctx.pop()


def test_post(test_client):
    post = Post(pagetitle='ptitle', alias='posttest', content='tcontent', status=4)
    db.session.add(post)
    db.session.commit()
    rv = test_client.get('/posttest')
    assert rv.status == '200 OK'
    assert b'tcontent' in rv.data
    assert b'ptitle' in rv.data


def test_post_index(test_client):
    rv = test_client.get('/')
    assert rv.status == '200 OK'
    assert b'ptitle' in rv.data


