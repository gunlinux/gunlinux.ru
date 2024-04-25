import pytest
import os

from blog import create_app
from blog import db


@pytest.fixture()
def test_client():
    os.environ["FLASK_ENV"] = "testing"
    app = create_app()
    app.config.update(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"}
    )
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.session.remove()
            db.drop_all()


def test_empty_db(test_client):
    """Start with a blank database."""
    rv = test_client.get("/")
    assert b"page__content" in rv.data


def test_app_is_testing(test_client):
    assert test_client.application.config["TESTING"] is True


def test_rss(test_client):
    rv = test_client.get("/rss.xml")
    assert rv.status_code == 200
    assert rv.mimetype == "application/rss+xml"
