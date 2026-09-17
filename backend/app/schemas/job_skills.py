from datetime import datetime
from pydantic import BaseModel,ConfigDict

class JobSkillCreate(BaseModel):
    job_id:int
    skill_id:str

class JobSkillResponse(JobSkillCreate):
    id:int
    created_at:datetime
    model_config=ConfigDict(from_attributes=True)
    