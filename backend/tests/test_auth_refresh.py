from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from fastapi import HTTPException

from app.api.auth import refresh_token, logout
from app.models.users import User
from app.models.refresh_tokens import RefreshToken
from app.schemas.token import TokenRefreshRequest
from app.auth.jwt import create_refresh_token


def test_refresh_token_success():
    mock_db = MagicMock()
    mock_user = User(
        id=1,
        email="test@example.com",
        hashed_password="hash",
        full_name="Test User",
        role="student",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    token_str, expires_at = create_refresh_token(data={"sub": "test@example.com", "user_id": 1})

    db_token = RefreshToken(
        id=1,
        token=token_str,
        user_id=1,
        revoked=False,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        created_at=datetime.now(timezone.utc),
    )

    # get_user_by_email -> mock_user
    # get_refresh_token_record -> db_token
    mock_exec_user = MagicMock()
    mock_exec_user.scalar_one_or_none.return_value = mock_user
    mock_exec_token = MagicMock()
    mock_exec_token.scalar_one_or_none.return_value = db_token

    mock_db.execute.side_effect = [mock_exec_user, mock_exec_token]

    req = TokenRefreshRequest(refresh_token=token_str)
    res = refresh_token(body=req, db=mock_db)

    assert res.access_token is not None
    assert res.refresh_token is not None
    assert res.token_type == "bearer"
    # Verify old token was revoked
    assert db_token.revoked is True


def test_refresh_token_revoked():
    mock_db = MagicMock()
    mock_user = User(
        id=1,
        email="test@example.com",
        hashed_password="hash",
        full_name="Test User",
        role="student",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    token_str, expires_at = create_refresh_token(data={"sub": "test@example.com", "user_id": 1})

    db_token = RefreshToken(
        id=1,
        token=token_str,
        user_id=1,
        revoked=True,  # Already revoked
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        created_at=datetime.now(timezone.utc),
    )

    mock_exec_user = MagicMock()
    mock_exec_user.scalar_one_or_none.return_value = mock_user
    mock_exec_token = MagicMock()
    mock_exec_token.scalar_one_or_none.return_value = db_token

    mock_db.execute.side_effect = [mock_exec_user, mock_exec_token]

    req = TokenRefreshRequest(refresh_token=token_str)
    try:
        refresh_token(body=req, db=mock_db)
        assert False, "Should have raised 401"
    except HTTPException as exc:
        assert exc.status_code == 401
        assert "Invalid, expired, or revoked" in exc.detail


def test_logout_success():
    mock_db = MagicMock()
    db_token = RefreshToken(
        id=1,
        token="some_token",
        user_id=1,
        revoked=False,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        created_at=datetime.now(timezone.utc),
    )

    mock_exec = MagicMock()
    mock_exec.scalar_one_or_none.return_value = db_token
    mock_db.execute.return_value = mock_exec

    req = TokenRefreshRequest(refresh_token="some_token")
    res = logout(body=req, db=mock_db)

    assert res == {"message": "Successfully logged out"}
    assert db_token.revoked is True
    assert mock_db.commit.called
