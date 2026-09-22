from typing import Any, List
try:
    from fastapi import APIRouter, Depends, status, HTTPException
except ImportError:
    class APIRouter:
        def __init__(self, *args, **kwargs):
            self.routes = []
        def post(self, path, **kwargs):
            def decorator(func):
                self.routes.append(("POST", path, func))
                return func
            return decorator
        def get(self, path, **kwargs):
            def decorator(func):
                self.routes.append(("GET", path, func))
                return func
            return decorator

    def Depends(dep):
        return dep

    class status:
        HTTP_200_OK = 200
        HTTP_201_CREATED = 201
        HTTP_404_NOT_FOUND = 404

    from ..services.ml_adapter import HTTPException

from ..db.session import get_db
from ..schemas.schemas import TargetRoleCreateSchema, TargetRoleResponseSchema
from ..services.role_service import RoleService
from ..auth.rbac import CurrentUser, require_role, get_current_user

router = APIRouter()

def _resolve_db(db: Any):
    if hasattr(db, "__next__") or (isinstance(db, type(get_db())) and hasattr(db, "send")):
        return next(db)
    elif hasattr(db, "dependency"):
        return next(get_db())
    return db

@router.get(
    "/",
    response_model=List[TargetRoleResponseSchema],
    status_code=status.HTTP_200_OK,
    summary="List all active target career roles"
)
def list_target_roles(
    db: Any = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user)
):
    actual_db = _resolve_db(db)
    return RoleService.list_roles(actual_db)

@router.get(
    "/{role_id}",
    response_model=TargetRoleResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Retrieve a specific target career role and its required skills"
)
def get_target_role(
    role_id: str,
    db: Any = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user)
):
    actual_db = _resolve_db(db)
    role = RoleService.get_role(actual_db, role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"TargetRole '{role_id}' not found.")
    return role

@router.post(
    "/",
    response_model=TargetRoleResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new target career role with required skills (Admin only)"
)
def create_target_role(
    role_in: TargetRoleCreateSchema,
    db: Any = Depends(get_db),
    _user: CurrentUser = Depends(require_role(["Admin"]))
):
    actual_db = _resolve_db(db)
    try:
        return RoleService.create_role(actual_db, role_in)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
