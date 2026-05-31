from app.auth.jwt import create_access_token, decode_token


def test_jwt_roundtrip():
    token = create_access_token("testuser")
    assert isinstance(token, str)
    assert decode_token(token) == "testuser"


def test_jwt_invalid():
    assert decode_token("not-a-valid-token") is None
