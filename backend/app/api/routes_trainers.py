"""
Trainer Intervention Routes — Phase 1 Loop D

Endpoints
---------
POST   /api/v1/trainers/interventions
    Create a new student intervention.  Trainer or Admin only.

GET    /api/v1/trainers/interventions
    List all interventions created by the authenticated trainer.

GET    /api/v1/trainers/interventions/{student_id}
    List all interventions received by a specific student.
    Trainer/Admin only — students cannot query this endpoint.

All endpoints require a valid JWT Bearer token.
"""
from typing import List

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.auth.rbac import CurrentUser, get_current_user
from app.schemas.trainer_interventions import (
    TrainerInterventionCreateSchema,
    TrainerInterventionResponseSchema,
)
from app.services.trainer_service import TrainerService

router = APIRouter()

# ────────────────────────────────────────────────────────────────────────────
# Helper — role guard (trainer or admin)
# ────────────────────────────────────────────────────────────────────────────

def _require_trainer_or_admin(user: CurrentUser) -> None:
    """Raise 403 if the authenticated user is neither trainer nor admin."""
    role = getattr(user, "role", "").lower()
    if role not in ("trainer", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Role '{getattr(user, 'role', '')}' is not permitted to access trainer endpoints. "
                "Required: trainer or admin."
            ),
        )


# ────────────────────────────────────────────────────────────────────────────
# POST /trainers/interventions
# ────────────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=TrainerInterventionResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a trainer intervention for a student",
    description=(
        "Assigns a skill intervention to a student. "
        "After the record is persisted the student's readiness gap is recalculated "
        "and the updated metrics are embedded in the response. "
        "Accessible by **Trainer** and **Admin** roles only."
    ),
)
def create_intervention(
    payload: TrainerInterventionCreateSchema,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> TrainerInterventionResponseSchema:
    _require_trainer_or_admin(current_user)
    try:
        return TrainerService.create_intervention(db, current_user.user_id, payload)
    except HTTPException:
        raise
    except Exception as e:
        if hasattr(db, "rollback"):
            db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error creating intervention: {str(e)}",
        )


# ────────────────────────────────────────────────────────────────────────────
# GET /trainers/interventions
# ────────────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=List[TrainerInterventionResponseSchema],
    status_code=status.HTTP_200_OK,
    summary="List all interventions created by the authenticated trainer",
    description=(
        "Returns the full intervention history submitted by the currently "
        "logged-in trainer, sorted newest-first. "
        "Accessible by **Trainer** and **Admin** roles only."
    ),
)
def list_trainer_interventions(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> List[TrainerInterventionResponseSchema]:
    _require_trainer_or_admin(current_user)
    try:
        return TrainerService.get_trainer_interventions(db, current_user.user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error fetching interventions: {str(e)}",
        )


# ────────────────────────────────────────────────────────────────────────────
# GET /trainers/interventions/{student_id}
# ────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{student_id}",
    response_model=List[TrainerInterventionResponseSchema],
    status_code=status.HTTP_200_OK,
    summary="List all interventions received by a specific student",
    description=(
        "Returns the full intervention history for the specified student. "
        "Accessible by **Trainer** and **Admin** roles only. "
        "Students are not permitted to query this endpoint."
    ),
)
def list_student_interventions(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> List[TrainerInterventionResponseSchema]:
    _require_trainer_or_admin(current_user)
    try:
        return TrainerService.get_student_interventions(db, student_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error fetching student interventions: {str(e)}",
        )
