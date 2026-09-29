from datetime import datetime, timedelta, timezone
from typing import Any
import uuid
from jose import JWTError, jwt

from app.config import settings


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "access",
        "jti": str(uuid.uuid4()),
    })
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def create_refresh_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> tuple[str, datetime]:
    """Creates a signed refresh token using dedicated REFRESH_SECRET_KEY and returns (token_string, expires_at)."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
    })
    token = jwt.encode(
        to_encode,
        settings.REFRESH_SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return token, expire


def verify_token(token: str, expected_type: str | None = None) -> dict[str, Any] | None:
    """
    Verifies a JWT token against the appropriate key (access or refresh).
    Supports token type enforcement and safe fallback.
    """
    keys_to_try = []
    if expected_type == "refresh":
        keys_to_try = [settings.REFRESH_SECRET_KEY, settings.SECRET_KEY]
    elif expected_type == "access":
        keys_to_try = [settings.SECRET_KEY]
    else:
        keys_to_try = [settings.SECRET_KEY, settings.REFRESH_SECRET_KEY]

    for key in keys_to_try:
        try:
            payload = jwt.decode(
                token,
                key,
                algorithms=[settings.ALGORITHM],
            )
            if expected_type is not None:
                token_type = payload.get("type")
                # If expected is access and type is missing, accept for backward compatibility
                if token_type is not None and token_type != expected_type:
                    return None
                if token_type is None and expected_type != "access":
                    return None
            return payload
        except JWTError:
            continue
    return None
