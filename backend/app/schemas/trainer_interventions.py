"""
Pydantic schemas for TrainerIntervention (Phase 1 — Loop D).
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from pydantic import BaseModel, Field, ConfigDict, model_validator


# Valid values — mirrored from TrainerService for consistent validation messages
VALID_INTERVENTION_TYPES = {
    "coaching",
    "assessment",
    "workshop",
    "mentoring",
    "course_assignment",
    "feedback",
}

VALID_PROFICIENCY_LEVELS = {"basic", "intermediate", "advanced"}


class TrainerInterventionCreateSchema(BaseModel):
    """
    Payload sent by the Trainer Portal when assigning a new intervention.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)

    student_id: int = Field(..., description="User ID of the student receiving the intervention")
    skill_id: int = Field(..., description="Integer PK of the target skill")
    intervention_type: str = Field(
        default="coaching",
        description=(
            "Category of intervention. "
            "One of: coaching, assessment, workshop, mentoring, course_assignment, feedback"
        ),
    )
    notes: Optional[str] = Field(default=None, description="Free-form notes from the trainer")
    proficiency_before: Optional[str] = Field(
        default=None,
        description="Trainer's assessment of student level before intervention (basic/intermediate/advanced)"
    )
    proficiency_after: Optional[str] = Field(
        default=None,
        description="Trainer's assessment of student level after intervention (basic/intermediate/advanced)"
    )

    @model_validator(mode="before")
    @classmethod
    def normalise_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Normalise intervention_type to lowercase
            it = data.get("intervention_type")
            if it:
                data["intervention_type"] = str(it).strip().lower()

            # Normalise proficiency fields to lowercase
            for field in ("proficiency_before", "proficiency_after"):
                val = data.get(field)
                if val:
                    data[field] = str(val).strip().lower()
        return data


class TrainerInterventionResponseSchema(BaseModel):
    """
    Response returned after creating or listing trainer interventions.
    Includes optional gap recalculation data embedded at creation time.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)

    id: int
    trainer_id: int
    student_id: int
    skill_id: int
    skill_name: Optional[str] = None
    skill_code: Optional[str] = None
    intervention_type: str
    notes: Optional[str] = None
    proficiency_before: Optional[str] = None
    proficiency_after: Optional[str] = None
    is_verified: bool = False
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Readiness recalculation result embedded in create response
    recalculated_gap: Optional[Dict[str, Any]] = None
