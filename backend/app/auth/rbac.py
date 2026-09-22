from typing import List, Optional
from pydantic import BaseModel

try:
    from fastapi import HTTPException, status, Header, Depends
except ImportError:
    from ..services.ml_adapter import HTTPException, status

    def Header(default=None, **kwargs):
        return default

    def Depends(dependency):
        return dependency

class CurrentUser(BaseModel):
    user_id: int = 1
    email: str = "user@worknexus.org"
    role: str = "Employer" # "Admin", "Institute", "Employer", "Trainer", "Student"

def get_current_user(
    x_user_id: Optional[int] = Header(default=1, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(default="Employer", alias="X-User-Role"),
    x_user_email: Optional[str] = Header(default="user@worknexus.org", alias="X-User-Email"),
) -> CurrentUser:
    """
    Standard dependency resolving authenticated user context from headers / JWT.
    """
    if not x_user_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials"
        )
    return CurrentUser(user_id=x_user_id or 1, email=x_user_email or "user@worknexus.org", role=x_user_role)

def require_role(allowed_roles: List[str]):
    def role_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        user = current_user
        if hasattr(user, "dependency"):
            user = get_current_user()
        if not user or user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{getattr(user, 'role', None)}' not permitted. Required one of: {allowed_roles}"
            )
        return user
    return role_checker
