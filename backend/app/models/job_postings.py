from datetime import datetime
from sqlalchemy import String, DateTime, Text,func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class JobPosting(Base):
    __tablename__ = "job_postings"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location:Mapped[str | None]=mapped_column(String(255))
    source:Mapped[str | None]=mapped_column(String(100))
    posted_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False,)

