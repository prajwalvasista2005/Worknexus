from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.jwt import verify_token
from app.db.dependencies import get_db
from app.models.users import User
from app.models.employers import Employer
from app.services.auth_service import AuthService
from app.services.employer_service import EmployerService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    x_user_id: Optional[int] = Header(default=None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(default=None, alias="X-User-Role"),
    x_user_email: Optional[str] = Header(default=None, alias="X-User-Email"),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    raw_token = token
    if not raw_token and authorization and authorization.startswith("Bearer "):
        raw_token = authorization[7:].strip()

    if raw_token:
        payload = verify_token(raw_token, expected_type="access")
        if payload is None:
            raise credentials_exception

        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception

        user = AuthService.get_user_by_email(db, email=email)
        if user is None:
            raise credentials_exception

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user",
            )
        return user

    # Development / testing X-User header support
    from app.config import settings
    if settings.ENVIRONMENT != "production" and (x_user_role or x_user_id or x_user_email):
        uid = x_user_id or 1
        user = AuthService.get_user_by_id(db, user_id=uid)
        if user:
            return user
        if x_user_email:
            user = AuthService.get_user_by_email(db, email=x_user_email)
            if user:
                return user
        return User(
            id=uid,
            email=x_user_email or "testuser@worknexus.org",
            full_name="Test User",
            role=x_user_role or "student",
            is_active=True,
        )

    raise credentials_exception


def get_current_employer(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    x_user_id: Optional[int] = Header(default=None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(default=None, alias="X-User-Role"),
    x_user_email: Optional[str] = Header(default=None, alias="X-User-Email"),
    db: Session = Depends(get_db),
) -> Employer:
    """
    Authentication dependency that:
    1. Authenticates current user from JWT token or test headers.
    2. Verifies employer role.
    3. Loads the Employer profile via user_id.
    4. Returns the Employer entity (primary key = employer.id).
    Never uses current_user.id as employer_id.
    """
    from app.auth.rbac import get_current_user as rbac_get_current_user
    current_user = rbac_get_current_user(
        x_user_id=x_user_id,
        x_user_role=x_user_role,
        x_user_email=x_user_email,
        authorization=authorization,
    )

    actual_db = next(db) if hasattr(db, "__next__") else db
    role = (current_user.role or "").strip().lower()
    if role not in ["employer", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User role '{current_user.role}' not permitted to perform employer operations. Required: Employer or Admin."
        )

    employer = EmployerService.get_employer_by_user_id(actual_db, current_user.user_id)
    if not employer:
        employer = EmployerService.get_or_create_employer_by_user_id(
            actual_db,
            user_id=current_user.user_id,
        )

    if not employer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employer profile not found for user {current_user.user_id}."
        )

    return employer
