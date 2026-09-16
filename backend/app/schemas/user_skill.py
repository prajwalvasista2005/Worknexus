from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class UserSkillCreate(BaseModel):
    skill_id: int
    proficiency_level: str = Field(default="beginner", description="Proficiency level: beginner, intermediate, advanced, expert")
    source: str = Field(default="self_reported", description="Source: self_reported, assessment, course_completion, resume_extraction")


class UserSkillUpdate(BaseModel):
    proficiency_level: str | None = None
    source: str | None = None


class UserSkillResponse(BaseModel):
    id: int
    user_id: int
    skill_id: int
    proficiency_level: str
    source: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
