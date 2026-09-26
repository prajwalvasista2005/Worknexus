from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Employer(Base):
    __tablename__ = "employers"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,
        index=True,
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    trust_weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship(
        "User",
        back_populates="employer_profile",
    )
    feedbacks: Mapped[List["EmployerFeedback"]] = relationship(
        "EmployerFeedback",
        back_populates="employer",
        cascade="all, delete-orphan",
    )


class EmployerFeedback(Base):
    __tablename__ = "employer_feedback"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    employer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("employers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    course_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    comments: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    employer: Mapped["Employer"] = relationship("Employer", back_populates="feedbacks")
    signals: Mapped[List["EmployerFeedbackSignal"]] = relationship(
        "EmployerFeedbackSignal",
        back_populates="feedback",
        cascade="all, delete-orphan",
    )


class EmployerFeedbackSignal(Base):
    __tablename__ = "employer_feedback_signals"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    feedback_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("employer_feedback.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    confidence_score: Mapped[float] = mapped_column(Float, default=0.95, nullable=False)
    trust_weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    weighted_signal: Mapped[float] = mapped_column(Float, default=0.95, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    feedback: Mapped["EmployerFeedback"] = relationship("EmployerFeedback", back_populates="signals")
