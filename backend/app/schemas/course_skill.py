from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class CourseSkillCreate(BaseModel):
    course_id: int = Field(..., description="Internal integer ID of the course")
    skill_id: int = Field(..., description="Internal integer ID of the skill")


class CourseSkillResponse(BaseModel):
    id: int
    course_id: int
    skill_id: int
    created_at: datetime
    skill_name: str | None = None
    skill_code: str | None = None

    model_config = ConfigDict(from_attributes=True)
