"""
Phase 5 Production Readiness & Hardening Tests.

Validates:
1. Request Correlation (X-Request-ID propagation, generation, and sensitive data masking)
2. Security Headers (nosniff, DENY, referrer-policy, permissions-policy)
3. Rate Limiting (in-memory sliding window, 429 responses, Retry-After header)
4. Database Engine Resilience & Graceful Lifespan
"""

import re
import uuid
import logging
import pytest
from fastapi.testclient import TestClient

from app.main import app, lifespan
from app.middleware import (
    get_request_id,
    RequestIdFilter,
    SensitiveDataFilter,
    rate_limiter_instance,
)
from app.db.session import engine


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Reset in-memory rate limiter state before each test."""
    rate_limiter_instance.clear()
    yield
    rate_limiter_instance.clear()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


# =============================================================================
# 1. Request Correlation & Structured Logging Tests
# =============================================================================

def test_request_id_generated_when_missing(client):
    """When X-Request-ID is not provided, the middleware generates a valid UUID v4."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    req_id = response.headers["X-Request-ID"]
    # Verify it is a valid UUID
    parsed = uuid.UUID(req_id)
    assert parsed.version == 4


def test_request_id_propagated_when_provided(client):
    """When X-Request-ID is provided in request headers, it is preserved in the response."""
    custom_id = "corr-test-id-abcdef-98765"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_id


def test_sensitive_data_log_filter():
    """SensitiveDataFilter masks raw passwords, access tokens, refresh tokens, and JWTs."""
    filt = SensitiveDataFilter()

    # Test JSON password masking
    rec1 = logging.LogRecord("test", logging.INFO, "test.py", 10, '{"email": "user@test.com", "password": "supersecretpassword123"}', (), None)
    filt.filter(rec1)
    assert "supersecretpassword123" not in rec1.msg
    assert '"password":"[REDACTED]"' in rec1.msg or '"password": "[REDACTED]"' in rec1.msg

    # Test Bearer token masking
    jwt_sample = (
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        + ".eyJzdWIiOiIxMjM0NTY3ODkwIn0"
        + ".doNotLeakThisSignature"
    )  # gitleaks:allow
    rec2 = logging.LogRecord("test", logging.INFO, "test.py", 11, f"Authenticating with {jwt_sample}", (), None)
    filt.filter(rec2)
    assert "doNotLeakThisSignature" not in rec2.msg
    assert "Bearer [REDACTED]" in rec2.msg

    # Test refresh token masking
    rec3 = logging.LogRecord("test", logging.INFO, "test.py", 12, 'Received "refresh_token": "secret_refresh_token_abc"', (), None)
    filt.filter(rec3)
    assert "secret_refresh_token_abc" not in rec3.msg
    assert '"refresh_token": "[REDACTED]"' in rec3.msg or '"refresh_token":"[REDACTED]"' in rec3.msg


# =============================================================================
# 2. Security Headers & CORS Tests
# =============================================================================

def test_security_headers_present_on_endpoints(client):
    """All responses must contain the 4 mandatory production security headers."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert response.headers.get("Permissions-Policy") == "camera=(), microphone=(), geolocation=()"


def test_cors_headers_for_allowed_origins(client):
    """CORS headers must be returned for allowed origins."""
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"


# =============================================================================
# 3. Rate Limiting Tests
# =============================================================================

def test_login_rate_limiting_enforcement(client):
    """POST /api/v1/auth/login limits requests to 5 per minute per IP."""
    payload = {"email": "nonexistent@test.com", "password": "wrongpassword"}
    client_ip = "198.51.100.1"

    # Make 5 attempts
    for i in range(5):
        resp = client.post(
            "/api/v1/auth/login",
            json=payload,
            headers={"X-Forwarded-For": client_ip},
        )
        assert resp.status_code != 429, f"Request {i+1} was unexpectedly rate limited"

    # 6th attempt should be blocked with 429
    blocked_resp = client.post(
        "/api/v1/auth/login",
        json=payload,
        headers={"X-Forwarded-For": client_ip},
    )
    assert blocked_resp.status_code == 429
    assert "Rate limit exceeded" in blocked_resp.json()["detail"]
    assert "Retry-After" in blocked_resp.headers
    assert int(blocked_resp.headers["Retry-After"]) > 0
    # X-Request-ID is attached
    assert "X-Request-ID" in blocked_resp.headers

    # Another IP should not be blocked
    other_ip_resp = client.post(
        "/api/v1/auth/login",
        json=payload,
        headers={"X-Forwarded-For": "198.51.100.2"},
    )
    assert other_ip_resp.status_code != 429


def test_register_rate_limiting_enforcement(client):
    """POST /api/v1/auth/register limits requests to 5 per minute per IP."""
    payload = {
        "email": "ratelimit_reg@test.com",
        "password": "Password123!",
        "full_name": "RL Test",
        "role": "student",
    }
    client_ip = "198.51.100.10"

    for i in range(5):
        resp = client.post(
            "/api/v1/auth/register",
            json=payload,
            headers={"X-Forwarded-For": client_ip},
        )
        assert resp.status_code != 429

    blocked_resp = client.post(
        "/api/v1/auth/register",
        json=payload,
        headers={"X-Forwarded-For": client_ip},
    )
    assert blocked_resp.status_code == 429
    assert "Rate limit exceeded" in blocked_resp.json()["detail"]


def test_non_auth_endpoints_not_rate_limited(client):
    """Non-auth endpoints (e.g., /health, GET /) are not subjected to auth rate limiting."""
    client_ip = "198.51.100.50"
    for _ in range(10):
        resp = client.get("/health", headers={"X-Forwarded-For": client_ip})
        assert resp.status_code == 200


# =============================================================================
# 4. Engine Resilience & Lifespan Tests
# =============================================================================

def test_engine_pool_pre_ping_configured():
    """Verify that SQLAlchemy engine has pool_pre_ping enabled."""
    # Under test harness engine might be SQLite, but real engine has pool_pre_ping=True
    from app.db.session import engine_kwargs
    assert engine_kwargs.get("pool_pre_ping") is True


import asyncio

def test_lifespan_lifecycle():
    """Verify lifespan context manager initializes and disposes cleanly."""
    async def _run():
        async with lifespan(app):
            pass

    asyncio.run(_run())
