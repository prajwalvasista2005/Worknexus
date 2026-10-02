"""
TrainerIntervention — Phase 1 Loop D model.

Records every deliberate trainer action on a student's skill competency.
After creation, triggers a readiness / gap recalculation so student metrics
stay current without any manual refresh.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Integer, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TrainerIntervention(Base):
    """
    Captures a trainer-issued skill intervention for a student.

    Columns
    -------
    id                  PK — auto-incremented integer (consistent with the rest of the schema)
    trainer_id          FK → users.id  (role == 'trainer')
    student_id          FK → users.id  (role == 'student')
    skill_id            FK → skills.id
    intervention_type   Free-form category tag: "coaching" | "assessment" | "workshop" |
                        "mentoring" | "course_assignment" | "feedback"
    notes               Long-form free text written by the trainer
    proficiency_before  Trainer's snapshot of the student's level before intervention
    proficiency_after   Trainer's assessment after intervention completes
    is_verified         Admin / system confirmation flag (default False at creation)
    created_at          UTC timestamp of record insertion
    """

    __tablename__ = "trainer_interventions"
    __table_args__ = (
        Index("ix_ti_trainer_id", "trainer_id"),
        Index("ix_ti_student_id", "student_id"),
        Index("ix_ti_skill_id", "skill_id"),
        Index("ix_ti_created_at", "created_at"),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    trainer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    intervention_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="coaching",
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Optional before/after proficiency snapshots (trainer's qualitative assessment)
    proficiency_before: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    proficiency_after: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Verification flag — False at creation; an admin/system process may set it True
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                         #
    # ------------------------------------------------------------------ #
    trainer = relationship(
        "User",
        foreign_keys=[trainer_id],
        lazy="select",
    )
    student = relationship(
        "User",
        foreign_keys=[student_id],
        lazy="select",
    )
    skill = relationship(
        "Skill",
        foreign_keys=[skill_id],
        lazy="select",
    )
