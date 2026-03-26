import pytest
import os
from pathlib import Path

from blog import create_app
from blog.extensions import db


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


def test_robots_txt_success(test_client):
    """Test successful robots.txt retrieval."""
    response = test_client.get("/robots.txt")
    assert response.status_code == 200
    assert response.mimetype == "text/plain"
    assert b"User-agent:" in response.data


def test_robots_txt_content(test_client):
    """Test that robots.txt contains expected content."""
    response = test_client.get("/robots.txt")
    assert response.status_code == 200
    assert b"User-agent:" in response.data
    assert b"Allow:" in response.data


def test_robots_txt_file_not_found(test_client, monkeypatch):
    """Test 404 handling when robots.txt file is missing."""
    # Temporarily rename the robots.txt file
    project_root = Path(__file__).parent.parent
    robots_file = project_root / "robots.txt"
    backup_file = project_root / "robots.txt.backup"

    if robots_file.exists():
        robots_file.rename(backup_file)

    try:
        response = test_client.get("/robots.txt")
        assert response.status_code == 404
    finally:
        # Restore the file
        if backup_file.exists():
            backup_file.rename(robots_file)
