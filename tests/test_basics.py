import pytest
import os

from blog import create_app
from blog import db


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


def test_empty_db(test_client):
    """Start with a blank database."""
    rv = test_client.get('/')
    assert b'page__content' in rv.data


def test_app_is_testing(test_client):
    assert test_client.application.config['TESTING'] is True


def test_rss(test_client):
    rv = test_client.get('/rss.xml')
    assert rv.status_code == 200
    assert rv.mimetype == 'application/rss+xml'
