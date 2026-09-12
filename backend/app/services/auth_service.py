from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.users import User
from app.schemas.user import UserCreate
from app.auth.security import hash_password, verify_password


class AuthService:

    @staticmethod
    def get_user_by_email(
        db: Session,
        email: str
    ) -> User | None:
        stmt = select(User).where(User.email == email)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_user_by_id(
        db: Session,
        user_id: int
    ) -> User | None:
        stmt = select(User).where(User.id == user_id)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def authenticate_user(
        db: Session,
        email: str,
        password: str
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
        user_data: UserCreate
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