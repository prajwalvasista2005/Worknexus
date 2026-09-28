import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.users import User
from app.models.refresh_tokens import RefreshToken
from app.auth.security import hash_password

client = TestClient(app)
PASSWORD = "SecurePassword123!"


@pytest.fixture
def test_user():
    email = "token_rotation_test@worknexus.io"
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                email=email,
                hashed_password=hash_password(PASSWORD),
                full_name="Rotation Tester",
                role="Student",
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        user_id = user.id
    return {"email": email, "password": PASSWORD, "user_id": user_id}


def test_refresh_token_rotation_and_revocation(test_user):
    """Verify that refresh token rotation returns a new token pair and revokes the old one."""
    # 1. Login to get initial tokens
    login_res = client.post("/api/v1/auth/login", json={"email": test_user["email"], "password": test_user["password"]})
    assert login_res.status_code == 200
    tokens_1 = login_res.json()
    refresh_token_1 = tokens_1["refresh_token"]

    # 2. First refresh -> 200 OK with new pair
    ref_res_1 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token_1})
    assert ref_res_1.status_code == 200
    tokens_2 = ref_res_1.json()
    refresh_token_2 = tokens_2["refresh_token"]
    assert refresh_token_2 != refresh_token_1

    # 3. Verify in DB that refresh_token_1 is revoked
    with SessionLocal() as db:
        record_1 = db.query(RefreshToken).filter(RefreshToken.token == refresh_token_1).first()
        assert record_1 is not None
        assert record_1.revoked is True

        record_2 = db.query(RefreshToken).filter(RefreshToken.token == refresh_token_2).first()
        assert record_2 is not None
        assert record_2.revoked is False

    # 4. Attempt to REPLAY old refresh_token_1 -> 401 Unauthorized
    replay_res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token_1})
    assert replay_res.status_code == 401


def test_refresh_token_replay_invalidates_family(test_user):
    """Verify that attempting to replay an old revoked token invalidates active tokens for the user."""
    # 1. Login
    login_res = client.post("/api/v1/auth/login", json={"email": test_user["email"], "password": test_user["password"]})
    tokens_1 = login_res.json()
    refresh_token_1 = tokens_1["refresh_token"]

    # 2. Rotate
    ref_res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token_1})
    assert ref_res.status_code == 200
    refresh_token_2 = ref_res.json()["refresh_token"]

    # 3. Replay token 1 (stolen token replay)
    replay_res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token_1})
    assert replay_res.status_code == 401

    # 4. Family invalidation: token 2 should now also be revoked
    subsequent_res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token_2})
    assert subsequent_res.status_code == 401


def test_logout_revokes_refresh_token(test_user):
    """Verify that logging out explicitly revokes the refresh token record in persistence."""
    # 1. Login
    login_res = client.post("/api/v1/auth/login", json={"email": test_user["email"], "password": test_user["password"]})
    tokens = login_res.json()
    refresh_token = tokens["refresh_token"]

    # 2. Logout
    logout_res = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout_res.status_code == 200
    assert logout_res.json()["message"] == "Successfully logged out"

    # 3. Verify DB record is revoked
    with SessionLocal() as db:
        record = db.query(RefreshToken).filter(RefreshToken.token == refresh_token).first()
        assert record is not None
        assert record.revoked is True

    # 4. Cannot refresh after logout
    ref_res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert ref_res.status_code == 401
