from typing import List, Any
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.schemas.schemas import (
    StudentProfileCreateSchema,
    StudentProfileResponseSchema,
    StudentSkillEvidenceCreateSchema,
    StudentSkillEvidenceResponseSchema
)
from app.services.student_service import StudentService
from app.auth.rbac import CurrentUser, require_role, get_current_user

router = APIRouter()


@router.post(
    "/profile",
    response_model=StudentProfileResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Create or update student profile target role"
)
def create_or_update_student_profile(
    profile_in: StudentProfileCreateSchema,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user)
):
    actual_db = next(db) if hasattr(db, "__next__") else db
    user_role = getattr(_user, "role", "").lower() if _user else ""
    if user_role != "admin" and getattr(_user, "user_id", None) != profile_in.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to modify another user's student profile."
        )
    try:
        return StudentService.create_or_get_profile(actual_db, profile_in)
    except HTTPException:
        if hasattr(actual_db, "rollback"):
            actual_db.rollback()
        raise
    except ValueError as e:
        if hasattr(actual_db, "rollback"):
            actual_db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        if hasattr(actual_db, "rollback"):
            actual_db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database transaction error: {str(e)}"
        )


@router.get(
    "/{user_id}/profile",
    response_model=StudentProfileResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Retrieve student profile and associated skill evidence"
)
def get_student_profile(
    user_id: int,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user)
):
    actual_db = next(db) if hasattr(db, "__next__") else db
    user_role = getattr(_user, "role", "").lower() if _user else ""
    if user_role == "student" and getattr(_user, "user_id", None) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students are not authorized to view other students' profiles."
        )

    try:
        profile = StudentService.get_profile_by_user_id(actual_db, user_id)
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"StudentProfile for User {user_id} not found.")
        return profile
    except HTTPException:
        if hasattr(actual_db, "rollback"):
            actual_db.rollback()
        raise
    except Exception as e:
        if hasattr(actual_db, "rollback"):
            actual_db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database transaction error: {str(e)}"
        )


@router.post(
    "/{user_id}/evidence",
    response_model=StudentSkillEvidenceResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a skill evidence record for a student"
)
def add_student_skill_evidence(
    user_id: int,
    evidence_in: StudentSkillEvidenceCreateSchema,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user)
):
    actual_db = next(db) if hasattr(db, "__next__") else db
    user_role = getattr(_user, "role", "").lower() if _user else ""
    if user_role != "admin" and getattr(_user, "user_id", None) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to add evidence for another user."
        )

    try:
        return StudentService.add_skill_evidence(actual_db, user_id, evidence_in)
    except HTTPException:
        if hasattr(actual_db, "rollback"):
            actual_db.rollback()
        raise
    except ValueError as e:
        if hasattr(actual_db, "rollback"):
            actual_db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        if hasattr(actual_db, "rollback"):
            actual_db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database transaction error: {str(e)}"
        )


@router.get(
    "/{user_id}/evidence",
    response_model=List[StudentSkillEvidenceResponseSchema],
    status_code=status.HTTP_200_OK,
    summary="List all skill evidence records for a student"
)
def list_student_skill_evidence(
    user_id: int,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user)
):
    actual_db = next(db) if hasattr(db, "__next__") else db
    if _user and getattr(_user, "role", "").lower() == "student" and _user.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Students are not authorized to view other students' evidence.")

    try:
        return StudentService.get_student_evidence(actual_db, user_id)
    except HTTPException:
        if hasattr(actual_db, "rollback"):
            actual_db.rollback()
        raise
    except Exception as e:
        if hasattr(actual_db, "rollback"):
            actual_db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database transaction error: {str(e)}"
        )
