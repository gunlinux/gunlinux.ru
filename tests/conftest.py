import pytest
import os
from blog import create_app
from blog.extensions import db, admin_ext

os.environ["FLASK_ENV"] = "testing"


@pytest.fixture()
def admin_app():
    os.environ["FLASK_ENV"] = "testing"
    test_app = create_app(init_admin=True)
    test_app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
        }
    )
    with test_app.app_context():
        db.create_all()
    yield test_app
    with test_app.app_context():
        db.session.remove()
        db.drop_all()
        admin_ext._views = []
        admin_ext._menu = []


@pytest.fixture()
def client_admin(admin_app):
    return admin_app.test_client()
