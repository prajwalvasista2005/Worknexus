"""
TrainerService — Phase 1 Loop D

Responsibilities
----------------
* create_intervention()      Validates trainer/student/skill, saves DB record,
                              triggers readiness recalculation.
* get_trainer_interventions() Returns all interventions created by a trainer.
* get_student_interventions() Returns all interventions received by a student.

Design notes
------------
- Follows the existing pattern established by StudentService, EmployerService, etc.
- DB branch only — no MockDatabaseSession path needed for this new feature.
- Gap recalculation reuses StudentService._recalculate_gap_isolated() so there
  is no duplicated ML logic.
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.trainer_interventions import TrainerIntervention
from app.models.users import User
from app.models.skills import Skill
from app.schemas.trainer_interventions import (
    TrainerInterventionCreateSchema,
    TrainerInterventionResponseSchema,
)

logger = logging.getLogger(__name__)

# Valid intervention type values — kept as a module constant so route-layer
# validation (Pydantic validator) and service-layer validation stay in sync.
VALID_INTERVENTION_TYPES = {
    "coaching",
    "assessment",
    "workshop",
    "mentoring",
    "course_assignment",
    "feedback",
}

VALID_PROFICIENCY_LEVELS = {"basic", "intermediate", "advanced", None}


class TrainerService:
    """Service layer for Trainer → Student intervention operations (Loop D)."""

    # ------------------------------------------------------------------
    # create_intervention
    # ------------------------------------------------------------------
    @staticmethod
    def create_intervention(
        db: Session,
        trainer_id: int,
        payload: TrainerInterventionCreateSchema,
    ) -> TrainerInterventionResponseSchema:
        """
        Validate → Save → Trigger readiness recalculation → Return.

        Raises HTTPException (400/404) on validation failures.
        Gap recalculation errors are non-fatal and are logged as warnings.
        """
        # 1. Validate trainer exists and has the correct role
        trainer: Optional[User] = db.query(User).filter(User.id == trainer_id).first()
        if not trainer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trainer user {trainer_id} not found.",
            )
        if trainer.role.lower() not in ("trainer", "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only users with role 'trainer' or 'admin' can create interventions.",
            )

        # 2. Validate student exists
        student: Optional[User] = db.query(User).filter(User.id == payload.student_id).first()
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student user {payload.student_id} not found.",
            )
        if student.role.lower() != "student":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User {payload.student_id} is not a student (role='{student.role}').",
            )

        # 3. Validate skill exists (resolve by integer PK)
        skill: Optional[Skill] = db.query(Skill).filter(Skill.id == payload.skill_id).first()
        if not skill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Skill with id={payload.skill_id} not found.",
            )

        # 4. Validate intervention_type
        if payload.intervention_type not in VALID_INTERVENTION_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid intervention_type '{payload.intervention_type}'. "
                    f"Must be one of: {sorted(VALID_INTERVENTION_TYPES)}"
                ),
            )

        # 5. Validate optional proficiency levels
        for field_name, field_val in [
            ("proficiency_before", payload.proficiency_before),
            ("proficiency_after", payload.proficiency_after),
        ]:
            if field_val is not None and field_val.lower() not in ("basic", "intermediate", "advanced"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Invalid {field_name} '{field_val}'. "
                        "Must be one of: basic, intermediate, advanced."
                    ),
                )

        # 6. Persist intervention record
        try:
            intervention = TrainerIntervention(
                trainer_id=trainer_id,
                student_id=payload.student_id,
                skill_id=skill.id,
                intervention_type=payload.intervention_type,
                notes=payload.notes,
                proficiency_before=payload.proficiency_before,
                proficiency_after=payload.proficiency_after,
                is_verified=False,
            )
            db.add(intervention)
            db.commit()
            db.refresh(intervention)
        except Exception as e:
            db.rollback()
            logger.error("Failed to persist trainer intervention: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save intervention: {str(e)}",
            ) from e

        # 7. Trigger readiness recalculation (non-fatal)
        gap_data: Dict[str, Any] = {}
        try:
            from app.services.student_service import StudentService

            # If the student has a profile with a target role, recalculate gap.
            # _recalculate_gap_isolated wraps the ML call in a SAVEPOINT so
            # any schema-drift errors can't contaminate the outer session.
            profile = StudentService.get_profile_by_user_id(db, payload.student_id)
            target_role_id = profile.target_role_id if profile else None
            gap_data = StudentService._recalculate_gap_isolated(db, payload.student_id, target_role_id)
            logger.info(
                "Readiness recalculation triggered for student %s after intervention %s",
                payload.student_id,
                intervention.id,
            )
        except Exception as e:
            logger.warning(
                "Gap recalculation after intervention %s failed (non-fatal): %s",
                intervention.id,
                e,
            )

        return TrainerService._to_response(intervention, skill, gap_data)

    # ------------------------------------------------------------------
    # get_trainer_interventions
    # ------------------------------------------------------------------
    @staticmethod
    def get_trainer_interventions(
        db: Session,
        trainer_id: int,
    ) -> List[TrainerInterventionResponseSchema]:
        """Return all interventions created by the specified trainer."""
        rows = (
            db.query(TrainerIntervention)
            .filter(TrainerIntervention.trainer_id == trainer_id)
            .order_by(TrainerIntervention.created_at.desc())
            .all()
        )
        return [TrainerService._to_response(row) for row in rows]

    # ------------------------------------------------------------------
    # get_student_interventions
    # ------------------------------------------------------------------
    @staticmethod
    def get_student_interventions(
        db: Session,
        student_id: int,
    ) -> List[TrainerInterventionResponseSchema]:
        """Return all interventions received by the specified student."""
        rows = (
            db.query(TrainerIntervention)
            .filter(TrainerIntervention.student_id == student_id)
            .order_by(TrainerIntervention.created_at.desc())
            .all()
        )
        return [TrainerService._to_response(row) for row in rows]

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------
    @staticmethod
    def _to_response(
        intervention: TrainerIntervention,
        skill: Optional[Skill] = None,
        gap_data: Optional[Dict[str, Any]] = None,
    ) -> TrainerInterventionResponseSchema:
        """Map ORM object → Pydantic response schema."""
        # Resolve skill display info — prefer the already-loaded object passed
        # in from create_intervention(); fall back to the lazy-loaded relationship.
        resolved_skill = skill or getattr(intervention, "skill", None)
        skill_name = getattr(resolved_skill, "name", None)
        skill_code = getattr(resolved_skill, "skill_id", None)

        return TrainerInterventionResponseSchema(
            id=intervention.id,
            trainer_id=intervention.trainer_id,
            student_id=intervention.student_id,
            skill_id=intervention.skill_id,
            skill_name=skill_name,
            skill_code=skill_code,
            intervention_type=intervention.intervention_type,
            notes=intervention.notes,
            proficiency_before=intervention.proficiency_before,
            proficiency_after=intervention.proficiency_after,
            is_verified=intervention.is_verified,
            created_at=intervention.created_at,
            recalculated_gap=gap_data or None,
        )
