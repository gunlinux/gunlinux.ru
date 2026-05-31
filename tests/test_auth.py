import pytest

from app.auth.jwt import create_access_token, decode_token


def test_jwt_roundtrip():
    token = create_access_token("testuser")
    assert isinstance(token, str)
    assert decode_token(token) == "testuser"


def test_jwt_invalid():
    assert decode_token("not-a-valid-token") is None


@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    response = await client.post(
        "/auth/login",
        data={"username": "nobody", "password": "wrong"},
        follow_redirects=False,
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout(client):
    response = await client.get("/auth/logout", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"
