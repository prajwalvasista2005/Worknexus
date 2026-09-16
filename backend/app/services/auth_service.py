from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.users import User
from app.models.refresh_tokens import RefreshToken
from app.schemas.user import UserCreate
from app.auth.security import hash_password, verify_password
from app.auth.jwt import create_access_token, create_refresh_token, verify_token


class AuthService:

    @staticmethod
    def get_user_by_email(
        db: Session,
        email: str,
    ) -> User | None:
        stmt = select(User).where(User.email == email)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_user_by_id(
        db: Session,
        user_id: int,
    ) -> User | None:
        stmt = select(User).where(User.id == user_id)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def authenticate_user(
        db: Session,
        email: str,
        password: str,
    ) -> User | None:
        user = AuthService.get_user_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    def create_user(
        db: Session,
        user_data: UserCreate,
    ) -> User:
        user = User(
            email=user_data.email,
            hashed_password=hash_password(user_data.password),
            full_name=user_data.full_name,
            role=user_data.role,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user

    @staticmethod
    def create_user_tokens(
        db: Session,
        user: User,
    ) -> tuple[str, str]:
        """Issues access token and refresh token, persisting refresh token to DB."""
        access_token = create_access_token(
            data={"sub": user.email, "role": user.role, "user_id": user.id}
        )
        refresh_token_str, expires_at = create_refresh_token(
            data={"sub": user.email, "user_id": user.id}
        )

        db_token = RefreshToken(
            token=refresh_token_str,
            user_id=user.id,
            expires_at=expires_at,
            revoked=False,
        )
        db.add(db_token)
        db.commit()

        return access_token, refresh_token_str

    @staticmethod
    def get_refresh_token_record(
        db: Session,
        token: str,
    ) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token == token)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def rotate_refresh_token(
        db: Session,
        old_token: str,
    ) -> tuple[str, str] | None:
        """
        Validates refresh token, revokes it, and issues a new access token and rotated refresh token.
        Returns (new_access_token, new_refresh_token) or None if invalid/expired/revoked.
        """
        payload = verify_token(old_token, expected_type="refresh")
        if not payload:
            return None

        email = payload.get("sub")
        if not email:
            return None

        user = AuthService.get_user_by_email(db, email=email)
        if not user or not user.is_active:
            return None

        db_token = AuthService.get_refresh_token_record(db, token=old_token)
        if not db_token or db_token.revoked:
            return None

        now = datetime.now(timezone.utc)
        if db_token.expires_at < now:
            return None

        # Revoke old token
        db_token.revoked = True

        # Generate new rotated token pair
        new_access_token = create_access_token(
            data={"sub": user.email, "role": user.role, "user_id": user.id}
        )
        new_refresh_token_str, new_expires_at = create_refresh_token(
            data={"sub": user.email, "user_id": user.id}
        )

        new_db_token = RefreshToken(
            token=new_refresh_token_str,
            user_id=user.id,
            expires_at=new_expires_at,
            revoked=False,
        )
        db.add(new_db_token)
        db.commit()

        return new_access_token, new_refresh_token_str

    @staticmethod
    def revoke_refresh_token(
        db: Session,
        token: str,
    ) -> bool:
        """Revokes a refresh token on logout."""
        db_token = AuthService.get_refresh_token_record(db, token=token)
        if not db_token:
            return False
        db_token.revoked = True
        db.commit()
        return True