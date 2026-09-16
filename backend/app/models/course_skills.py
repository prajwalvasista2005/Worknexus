from datetime import datetime, timezone
from sqlalchemy import Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CourseSkill(Base):
    __tablename__ = "course_skills"
    __table_args__ = (
        UniqueConstraint("course_id", "skill_id", name="uq_course_skills_course_skill"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )
    course_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    course = relationship("Course", back_populates="course_skills")
    skill = relationship("Skill", back_populates="course_skills")
