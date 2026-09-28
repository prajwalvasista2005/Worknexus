from datetime import datetime
from typing import Union
from pydantic import BaseModel, ConfigDict


class JobSkillCreate(BaseModel):
    job_id: int
    skill_id: Union[int, str]


class JobSkillResponse(BaseModel):
    id: int
    job_id: int
    skill_id: Union[int, str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
