# routes_students.py
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
        HTTP_403_FORBIDDEN = 403
        HTTP_404_NOT_FOUND = 404

    from ..services.ml_adapter import HTTPException

from typing import List
from ..db.session import get_db
from ..schemas.schemas import (
    StudentProfileResponseSchema,
    StudentSkillEvidenceCreateSchema,
    StudentSkillEvidenceResponseSchema
)
from ..services.student_service import StudentService
from ..auth.rbac import CurrentUser, require_role, get_current_user

router = APIRouter()

@router.get(
    "/{user_id}/profile",
    status_code=status.HTTP_200_OK,
    summary="Retrieve student profile and associated skill evidence"
)
def get_student_profile(
    user_id: int,
    db = None,
    _user: CurrentUser = None
):
    actual_db = db or next(get_db())
    # RBAC check: Student can view own profile; Institute and Admin can view any
    if _user and _user.role == "Student" and _user.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Students are not authorized to view other students' profiles.")

    profile = StudentService.get_profile_by_user_id(actual_db, user_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"StudentProfile for User {user_id} not found.")
    return profile

@router.post(
    "/{user_id}/evidence",
    status_code=status.HTTP_201_CREATED,
    summary="Submit a skill evidence record for a student"
)
def add_student_skill_evidence(
    user_id: int,
    evidence_in: StudentSkillEvidenceCreateSchema,
    db = None,
    _user: CurrentUser = None
):
    actual_db = db or next(get_db())
    # RBAC check: Student can add own evidence; Institute and Admin can add
    if _user and _user.role == "Student" and _user.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Students are not authorized to add evidence for other students.")

    try:
        return StudentService.add_skill_evidence(actual_db, user_id, evidence_in)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

@router.get(
    "/{user_id}/evidence",
    status_code=status.HTTP_200_OK,
    summary="List all skill evidence records for a student"
)
def list_student_skill_evidence(
    user_id: int,
    db = None,
    _user: CurrentUser = None
):
    actual_db = db or next(get_db())
    if _user and _user.role == "Student" and _user.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Students are not authorized to view other students' evidence.")

    return StudentService.get_student_evidence(actual_db, user_id)
