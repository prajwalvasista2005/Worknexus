from datetime import datetime,UTC
from sqlalchemy import func,ForeignKey,DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class JobSkill(Base):
    __tablename__="job_skills"
    id:Mapped[int]=mapped_column(primary_key=True)
    job_id:Mapped[int]=mapped_column(ForeignKey("job_postings.id"),nullable=False)
    skill_id:Mapped[str]=mapped_column(ForeignKey("skills.skill_id"),nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False,)

