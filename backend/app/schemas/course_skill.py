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

    model_config = ConfigDict(from_attributes=True)
