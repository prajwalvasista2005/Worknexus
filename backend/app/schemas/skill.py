from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class SkillCreate(BaseModel):
    skill_id: str = Field(..., max_length=50, description="Unique skill identifier code")
    name: str = Field(..., max_length=255, description="Skill name")
    category: str = Field(..., max_length=100, description="Category or industry sector")
    description: str | None = Field(default=None, max_length=500, description="Skill description")


class SkillUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    description: str | None = None
    is_active: bool | None = None


class SkillResponse(BaseModel):
    id: int
    skill_id: str
    name: str
    category: str
    description: str | None = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
