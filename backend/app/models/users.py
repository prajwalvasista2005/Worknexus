from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Index, CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email_lower", text("LOWER(email)"), unique=True),
        CheckConstraint(
            "role IN ('student', 'employer', 'institute', 'trainer', 'admin')",
            name="chk_users_role"
        ),
        {"extend_existing": True},
    )

    def __init__(self, **kwargs):
        if "hashed_password" not in kwargs:
            kwargs["hashed_password"] = "default_test_hashed_password"
        if "full_name" not in kwargs:
            kwargs["full_name"] = kwargs.get("email", "User")
        super().__init__(**kwargs)

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    skills = relationship(
        "UserSkill",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    refresh_tokens = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    student_profile = relationship(
        "StudentProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    employer_profile = relationship(
        "Employer",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

