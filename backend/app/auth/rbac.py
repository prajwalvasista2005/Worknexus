from typing import List, Optional
from pydantic import BaseModel
from fastapi import HTTPException, status, Header, Depends
from ..config import settings


class CurrentUser(BaseModel):
    user_id: int
    email: str
    role: str  # "Admin", "Institute", "Employer", "Trainer", "Student"


def get_current_user(
    x_user_id: Optional[int] = Header(default=None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(default=None, alias="X-User-Role"),
    x_user_email: Optional[str] = Header(default=None, alias="X-User-Email"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> CurrentUser:
    """
    Dependency resolving authenticated user context from JWT Bearer tokens.
    In development/testing mode only, accepts X-User headers for unit testing compatibility.
    Unauthenticated requests will raise HTTP 401 Unauthorized.
    """
    uid: Optional[int] = None
    urole: Optional[str] = None
    uemail: Optional[str] = None

    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        from .jwt import verify_token
        payload = verify_token(token, expected_type="access")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid, expired, or malformed authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        raw_uid = payload.get("user_id")
        uid = int(raw_uid) if raw_uid is not None else None
        uemail = payload.get("sub")
        urole = payload.get("role")

    # In development / testing environments only, support X-User headers for test clients
    elif settings.ENVIRONMENT != "production" and (x_user_role or x_user_id):
        uid = x_user_id or 1
        urole = x_user_role or "Student"
        uemail = x_user_email or "testuser@worknexus.org"

    if uid is None or urole is None or uemail is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication credentials. Bearer token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(user_id=uid, email=uemail, role=urole)


def require_role(allowed_roles: List[str]):
    def role_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        user = current_user
        if hasattr(user, "dependency"):
            user = get_current_user()
        if not user or not getattr(user, "role", None):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication credentials"
            )
        allowed_lower = [r.lower() for r in allowed_roles]
        if user.role.lower() not in allowed_lower:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{getattr(user, 'role', None)}' not permitted. Required one of: {allowed_roles}"
            )
        return user
    return role_checker

