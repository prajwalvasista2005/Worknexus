from datetime import timedelta
from jose import jwt

from app.config import settings
from app.auth.jwt import create_access_token, verify_token


def test_create_and_verify_token():
    payload_data = {"sub": "testuser@example.com", "role": "developer"}
    token = create_access_token(data=payload_data)
    assert isinstance(token, str)

    decoded = verify_token(token)
    assert decoded is not None
    assert decoded.get("sub") == "testuser@example.com"
    assert decoded.get("role") == "developer"
    assert "exp" in decoded


def test_verify_expired_token():
    payload_data = {"sub": "expired@example.com"}
    expired_token = create_access_token(
        data=payload_data,
        expires_delta=timedelta(seconds=-10)
    )
    decoded = verify_token(expired_token)
    assert decoded is None


def test_verify_invalid_token():
    invalid_token = "invalid.token.signature"
    decoded = verify_token(invalid_token)
    assert decoded is None


def test_verify_tampered_token():
    payload_data = {"sub": "user@example.com"}
    token = create_access_token(data=payload_data)
    tampered_token = token[:-5] + "aaaaa"
    decoded = verify_token(tampered_token)
    assert decoded is None
