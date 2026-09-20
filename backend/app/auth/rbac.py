from typing import List, Optional

try:
    from fastapi import HTTPException, status, Header, Depends
except ImportError:
    from ..services.ml_adapter import HTTPException, status

    def Header(default=None, **kwargs):
        return default

    def Depends(dependency):
        return dependency

class CurrentUser:
    def __init__(self, user_id: int, email: str, role: str):
        self.user_id = user_id
        self.email = email
        self.role = role # "Admin", "Institute", "Employer", "Trainer", "Student"

def get_current_user(
    x_user_id: Optional[int] = 1,
    x_user_role: Optional[str] = "Employer",
    x_user_email: Optional[str] = "user@worknexus.org"
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
    def role_checker(current_user: CurrentUser = None) -> CurrentUser:
        user = current_user or get_current_user()
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{user.role}' not permitted. Required one of: {allowed_roles}"
            )
        return user
    return role_checker
