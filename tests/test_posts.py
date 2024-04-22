import pytest
import os

from blog import create_app
from blog import db
from blog.post.models import Post


@pytest.fixture()
def test_client():
    os.environ['FLASK_ENV'] = 'testing'
    app = create_app()
    app.config.update({
        "TESTING": True,
    })
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.session.remove()
            db.drop_all()


def test_post(test_client):
    with test_client.application.app_context():
        post = Post(pagetitle='ptitle', alias='posttest', content='tcontent', status=4)
        db.session.add(post)
        db.session.commit()
    rv = test_client.get('/posttest')
    assert rv.status == '200 OK'
    assert b'tcontent' in rv.data
    print(rv.data)
    assert b'ptitle' in rv.data


def test_page(test_client):
    with test_client.application.app_context():
        testpage = Post(pagetitle='pagetitle', alias='pagealias', content='pagecontent', status=4)
        db.session.add(testpage)
        db.session.commit()
    rv = test_client.get('/pagealias')
    assert rv.status == '200 OK'
    assert b'pagecontent' in rv.data
    assert b'pagetitle' in rv.data


def test_post_index(test_client):
    with test_client.application.app_context():
        testpage = Post(pagetitle='pagetitle', alias='pagealias', content='pagecontent', status=4)
        db.session.add(testpage)
        db.session.commit()
    rv = test_client.get('/')
    assert rv.status == '200 OK'
    assert b'pagetitle' in rv.data


def test_page_index(test_client):
    with test_client.application.app_context():
        testpage = Post(pagetitle='pagetitle', alias='pagealias', content='pagecontent', status=4)
        db.session.add(testpage)
        db.session.commit()
    rv = test_client.get('/')
    assert rv.status == '200 OK'
    assert b'pagealias' in rv.data


