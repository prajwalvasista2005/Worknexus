from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Skill(Base):
    __tablename__ = "skills"
    __table_args__ = {"extend_existing": True}

    def __init__(self, **kwargs):
        if "id" in kwargs and isinstance(kwargs["id"], str) and "skill_id" not in kwargs:
            kwargs["skill_id"] = kwargs.pop("id")
        kwargs.pop("version", None)
        super().__init__(**kwargs)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False, index=True)
    skill_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user_skills = relationship(
        "UserSkill",
        back_populates="skill",
        cascade="all, delete-orphan",
    )
    course_skills = relationship(
        "CourseSkill",
        back_populates="skill",
        cascade="all, delete-orphan",
    )