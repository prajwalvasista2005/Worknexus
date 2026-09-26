from typing import List, Any
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.schemas.schemas import TargetRoleCreateSchema, TargetRoleResponseSchema
from app.services.role_service import RoleService
from app.auth.rbac import CurrentUser, require_role, get_current_user

router = APIRouter()


@router.get(
    "/",
    response_model=List[TargetRoleResponseSchema],
    status_code=status.HTTP_200_OK,
    summary="List all active target career roles"
)
def list_target_roles(
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user)
):
    actual_db = next(db) if hasattr(db, "__next__") else db
    return RoleService.list_roles(actual_db)


@router.get(
    "/{role_id}",
    response_model=TargetRoleResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Retrieve a specific target career role and its required skills"
)
def get_target_role(
    role_id: str,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user)
):
    actual_db = next(db) if hasattr(db, "__next__") else db
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
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role(["Admin"]))
):
    actual_db = next(db) if hasattr(db, "__next__") else db
    try:
        return RoleService.create_role(actual_db, role_in)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
