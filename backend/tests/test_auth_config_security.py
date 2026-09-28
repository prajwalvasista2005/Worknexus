import os
import pytest
from app.config import Settings, INSECURE_SECRET_KEYS, settings
from app.auth.jwt import create_access_token, create_refresh_token, verify_token


def test_production_rejects_default_secret_key():
    """Verify that validate_production_security() strictly raises RuntimeError for default/insecure SECRET_KEY."""
    s = Settings()
    s.ENVIRONMENT = "production"
    s.SECRET_KEY = "default-dev-secret-key-replace-in-production"
    s.REFRESH_SECRET_KEY = "a-very-long-and-secure-random-refresh-secret-key"

    with pytest.raises(RuntimeError) as exc:
        s.validate_production_security()
    assert "Insecure or default SECRET_KEY" in str(exc.value)


def test_production_rejects_empty_or_short_secret_key():
    """Verify that validate_production_security() strictly raises RuntimeError for empty or short SECRET_KEY."""
    s = Settings()
    s.ENVIRONMENT = "production"
    s.SECRET_KEY = "short"
    s.REFRESH_SECRET_KEY = "a-very-long-and-secure-random-refresh-secret-key"

    with pytest.raises(RuntimeError) as exc:
        s.validate_production_security()
    assert "Insecure or default SECRET_KEY" in str(exc.value)


def test_production_rejects_default_refresh_secret_key():
    """Verify that validate_production_security() strictly raises RuntimeError for default/insecure REFRESH_SECRET_KEY."""
    s = Settings()
    s.ENVIRONMENT = "production"
    s.SECRET_KEY = "a-very-long-and-secure-random-access-secret-key"
    s.REFRESH_SECRET_KEY = "default-dev-refresh-secret-key-replace-in-production"

    with pytest.raises(RuntimeError) as exc:
        s.validate_production_security()
    assert "Insecure or default REFRESH_SECRET_KEY" in str(exc.value)


def test_production_accepts_strong_keys():
    """Verify that validate_production_security() succeeds when both keys are strong in production."""
    s = Settings()
    s.ENVIRONMENT = "production"
    s.SECRET_KEY = "super-secret-production-access-key-12345"
    s.REFRESH_SECRET_KEY = "super-secret-production-refresh-key-67890"

    # Should not raise
    s.validate_production_security()


def test_development_allows_default_keys():
    """Verify that non-production environments allow default keys for local DX."""
    s = Settings()
    s.ENVIRONMENT = "development"
    s.SECRET_KEY = "default-dev-secret-key-replace-in-production"
    s.REFRESH_SECRET_KEY = "default-dev-refresh-secret-key-replace-in-production"

    # Should not raise
    s.validate_production_security()


def test_token_creation_and_verification_with_centralized_constants():
    """Verify that tokens created with centralized settings verify successfully with expected types."""
    data = {"sub": "user@worknexus.io", "user_id": 42, "role": "Student"}

    access_token = create_access_token(data)
    assert isinstance(access_token, str)

    payload_access = verify_token(access_token, expected_type="access")
    assert payload_access is not None
    assert payload_access["sub"] == "user@worknexus.io"
    assert payload_access["user_id"] == 42
    assert payload_access["type"] == "access"

    refresh_token, exp = create_refresh_token(data)
    assert isinstance(refresh_token, str)

    payload_refresh = verify_token(refresh_token, expected_type="refresh")
    assert payload_refresh is not None
    assert payload_refresh["sub"] == "user@worknexus.io"
    assert payload_refresh["user_id"] == 42
    assert payload_refresh["type"] == "refresh"

    # Type mismatch must fail verification
    assert verify_token(access_token, expected_type="refresh") is None
    assert verify_token(refresh_token, expected_type="access") is None
