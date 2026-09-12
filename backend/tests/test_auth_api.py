from datetime import datetime, timezone
from unittest.mock import MagicMock
from fastapi import HTTPException

from app.api.auth import login, get_me, register
from app.auth.dependencies import get_current_user
from app.models.users import User
from app.schemas.user import UserLogin, UserCreate
from app.auth.security import hash_password
from app.auth.jwt import create_access_token


def test_login_invalid_credentials():
    mock_db = MagicMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_execute

    creds = UserLogin(email="unknown@example.com", password="wrongpassword")
    try:
        login(credentials=creds, db=mock_db)
        assert False, "Should have raised HTTPException 401"
    except HTTPException as exc:
        assert exc.status_code == 401
        assert exc.detail == "Incorrect email or password"


def test_login_success():
    mock_db = MagicMock()
    hashed = hash_password("correctpassword")
    mock_user = User(
        id=1,
        email="test@example.com",
        hashed_password=hashed,
        full_name="Test User",
        role="admin",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_user
    mock_db.execute.return_value = mock_execute

    creds = UserLogin(email="test@example.com", password="correctpassword")
    token_response = login(credentials=creds, db=mock_db)

    assert token_response.access_token is not None
    assert token_response.token_type == "bearer"


def test_get_current_user_valid():
    mock_db = MagicMock()
    mock_user = User(
        id=1,
        email="test@example.com",
        hashed_password=hash_password("password"),
        full_name="Test User",
        role="admin",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_user
    mock_db.execute.return_value = mock_execute

    token = create_access_token(data={"sub": "test@example.com"})
    user = get_current_user(token=token, db=mock_db)

    assert user.id == 1
    assert user.email == "test@example.com"


def test_get_current_user_invalid_token():
    mock_db = MagicMock()
    try:
        get_current_user(token="invalid.token.here", db=mock_db)
        assert False, "Should have raised HTTPException 401"
    except HTTPException as exc:
        assert exc.status_code == 401
        assert exc.detail == "Could not validate credentials"


def test_get_me_endpoint():
    mock_user = User(
        id=1,
        email="test@example.com",
        hashed_password="hash",
        full_name="Test User",
        role="admin",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    res = get_me(current_user=mock_user)
    assert res.email == "test@example.com"
    assert res.full_name == "Test User"
