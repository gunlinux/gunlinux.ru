import pytest

from pro import create_app
from pro import db


@pytest.fixture
def client():
    app = create_app()

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client


def test_empty_db(client):
    """Start with a blank database."""

    rv = client.get('/')
    assert b'page__content' in rv.data


'''
import unittest
from flask import current_app
from pro import create_app, db


class BasicsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_app_exists(self):
        self.assertFalse(current_app is None)

    def test_app_is_testing(self):
        self.assertTrue(current_app.config['TESTING'])

'''
