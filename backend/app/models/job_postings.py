from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Integer, String, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from .jobSkill import JobSkill


class JobPosting(Base):
    __tablename__ = "job_postings"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    employer_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("employers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    posted_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    job_skills: Mapped[List["JobSkill"]] = relationship(
        "JobSkill",
        back_populates="job_posting",
        cascade="all, delete-orphan",
    )

    def __init__(self, **kwargs):
        if "company" in kwargs and "company_name" not in kwargs:
            kwargs["company_name"] = kwargs.pop("company")
        super().__init__(**kwargs)

    @property
    def company(self) -> str:
        return self.company_name

    @company.setter
    def company(self, value: str):
        self.company_name = value
