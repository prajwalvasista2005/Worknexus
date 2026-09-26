from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import Integer, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TargetRole(Base):
    __tablename__ = "target_roles"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    role_skills: Mapped[List["RoleSkill"]] = relationship(
        "RoleSkill",
        back_populates="role",
        cascade="all, delete-orphan",
    )


class RoleSkill(Base):
    __tablename__ = "role_skills"
    __table_args__ = (
        UniqueConstraint("role_id", "skill_id", name="uq_role_skill"),
        {"extend_existing": True}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("target_roles.id", ondelete="CASCADE"),
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

    role: Mapped["TargetRole"] = relationship("TargetRole", back_populates="role_skills")
    skill = relationship("Skill")


class StudentProfile(Base):
    __tablename__ = "student_profiles"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    target_role_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("target_roles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="student_profile")
    target_role = relationship("TargetRole")
    evidence_records: Mapped[List["StudentSkillEvidence"]] = relationship(
        "StudentSkillEvidence",
        back_populates="profile",
        cascade="all, delete-orphan",
    )


class StudentSkillEvidence(Base):
    __tablename__ = "student_skill_evidence"
    __table_args__ = {"extend_existing": True}

    VALID_EVIDENCE_TYPES = {
        "self_reported",
        "course_completed",
        "project",
        "certification",
        "assessment",
    }

    VALID_STRENGTH_CATEGORIES = {
        "basic",
        "intermediate",
        "advanced",
    }

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_profile_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evidence_type: Mapped[str] = mapped_column(String(32), nullable=False)
    strength: Mapped[str] = mapped_column(String(16), nullable=False)
    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    profile: Mapped["StudentProfile"] = relationship("StudentProfile", back_populates="evidence_records")
    skill = relationship("Skill")

    def __init__(self, **kwargs):
        if "metadata" in kwargs and "metadata_" not in kwargs:
            kwargs["metadata_"] = kwargs.pop("metadata")
        ev_type = kwargs.get("evidence_type")
        if ev_type and ev_type not in self.VALID_EVIDENCE_TYPES:
            raise ValueError(f"Invalid evidence_type '{ev_type}'. Must be one of: {sorted(list(self.VALID_EVIDENCE_TYPES))}")
        st = kwargs.get("strength")
        if st and st not in self.VALID_STRENGTH_CATEGORIES:
            raise ValueError(f"Invalid strength category '{st}'. Must be one of: {sorted(list(self.VALID_STRENGTH_CATEGORIES))}")
        super().__init__(**kwargs)

    def __getattribute__(self, name: str) -> Any:
        if name == "metadata":
            try:
                val = super().__getattribute__("metadata_")
                return val if isinstance(val, dict) else {}
            except AttributeError:
                return {}
        return super().__getattribute__(name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "metadata":
            super().__setattr__("metadata_", value)
        else:
            super().__setattr__(name, value)

