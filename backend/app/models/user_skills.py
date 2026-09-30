from datetime import datetime, timezone
from sqlalchemy import Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserSkill(Base):
    __tablename__ = "user_skills"
    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", name="uq_user_skills_user_skill"),
        {"extend_existing": True}
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
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
    proficiency_level: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="beginner",
    )
    source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="self_reported",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="skills")
    skill = relationship("Skill", back_populates="user_skills")

    @property
    def canonical_id(self):
        if getattr(self, "skill", None) and getattr(self.skill, "skill_id", None):
            return self.skill.skill_id
        from app.services.skill_service import SkillService
        tax = SkillService._lookup_taxonomy(str(self.skill_id))
        if tax:
            return tax[0]
        if isinstance(self.skill_id, str) and self.skill_id.startswith("SK_"):
            return self.skill_id
        return None

    @property
    def skill_name(self):
        if getattr(self, "skill", None) and getattr(self.skill, "name", None):
            return self.skill.name
        from app.services.skill_service import SkillService
        tax = SkillService._lookup_taxonomy(str(self.skill_id))
        if tax:
            return tax[1]
        return None

    @property
    def name(self):
        return self.skill_name

    @property
    def category(self):
        if getattr(self, "skill", None) and getattr(self.skill, "category", None):
            return self.skill.category
        from app.services.skill_service import SkillService
        tax = SkillService._lookup_taxonomy(str(self.skill_id))
        if tax:
            return tax[2]
        return "General"


# Alias StudentSkill to UserSkill for student profile inventory semantics
StudentSkill = UserSkill
