from datetime import datetime
from pydantic import BaseModel, ConfigDict

class JobPostingCreate(BaseModel):
    title:str
    company_name:str
    description:str
    location:str | None = None
    source:str | None = None
    posted_date:datetime | None = None

class JobPostingResponse(JobPostingCreate):
    id:int
    created_at:datetime

    model_config=ConfigDict(from_attributes=True)