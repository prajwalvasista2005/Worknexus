from typing import List, Any
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.employers import EmployerFeedback
from app.schemas.schemas import (
    EmployerFeedbackCreateSchema,
    EmployerFeedbackResponseSchema,
    EmployerProfileCreateSchema,
    EmployerProfileResponseSchema
)
from app.services.ml_adapter import MLAdapter, get_ml_adapter
from app.services.employer_service import EmployerService
from app.auth.rbac import require_role, get_current_user, CurrentUser

router = APIRouter()


@router.post(
    "/profile",
    response_model=EmployerProfileResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Create or update employer profile for authenticated user"
)
def create_or_update_employer_profile(
    profile_in: EmployerProfileCreateSchema,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role(["Employer", "Admin"]))
):
    actual_db = next(db) if hasattr(db, "__next__") else db
    employer = EmployerService.create_or_update_profile(
        db=actual_db,
        user_id=_user.user_id,
        company_name=profile_in.company_name,
        trust_weight=profile_in.trust_weight if profile_in.trust_weight is not None else 1.0
    )
    return employer


@router.get(
    "/profile",
    response_model=EmployerProfileResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Retrieve current authenticated employer profile"
)
def get_current_employer_profile(
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role(["Employer", "Admin"]))
):
    actual_db = next(db) if hasattr(db, "__next__") else db
    employer = EmployerService.get_employer_by_user_id(actual_db, _user.user_id)
    if not employer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employer profile not found for user {_user.user_id}."
        )
    return employer


@router.get(
    "/{user_id}/profile",
    response_model=EmployerProfileResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Retrieve employer profile by user ID"
)
def get_employer_profile_by_user_id(
    user_id: int,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user)
):
    actual_db = next(db) if hasattr(db, "__next__") else db
    employer = EmployerService.get_employer_by_user_id(actual_db, user_id)
    if not employer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employer profile not found for user {user_id}."
        )
    return employer


@router.post(
    "/feedback",
    response_model=EmployerFeedbackResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Submit structured employer feedback with automated skill intelligence"
)
def submit_employer_feedback(
    feedback_in: EmployerFeedbackCreateSchema,
    db: Session = Depends(get_db),
    ml_adapter: MLAdapter = Depends(get_ml_adapter),
    _user: CurrentUser = Depends(require_role(["Employer", "Admin"]))
) -> EmployerFeedbackResponseSchema:
    actual_db = next(db) if hasattr(db, "__next__") else db
    actual_adapter = ml_adapter if not hasattr(ml_adapter, "dependency") else get_ml_adapter()
    if _user and getattr(_user, "role", "").lower() == "employer":
        employer = EmployerService.get_employer_by_user_id(actual_db, _user.user_id)
        if employer:
            feedback_in.employer_id = employer.id
    return EmployerService.submit_feedback(db=actual_db, feedback_in=feedback_in, ml_adapter=actual_adapter)


@router.get(
    "/feedback",
    response_model=List[EmployerFeedbackResponseSchema],
    status_code=status.HTTP_200_OK,
    summary="List submitted employer feedbacks"
)
def list_employer_feedback(
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user)
) -> List[EmployerFeedbackResponseSchema]:
    actual_db = next(db) if hasattr(db, "__next__") else db
    if hasattr(actual_db, "query"):
        feedbacks = actual_db.query(EmployerFeedback).order_by(EmployerFeedback.id.desc()).all()
    elif hasattr(actual_db, "employer_feedback"):
        feedbacks = list(actual_db.employer_feedback.values())
    else:
        feedbacks = []

    return [
        EmployerFeedbackResponseSchema(
            id=fb.id,
            employer_id=fb.employer_id,
            course_id=fb.course_id,
            comments=fb.comments,
            rating=fb.rating,
            detected_signals=[],
            created_at=fb.created_at
        )
        for fb in feedbacks
    ]
