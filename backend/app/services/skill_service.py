from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.skills import Skill
from app.schemas.skill import SkillCreate, SkillUpdate


class SkillService:

    @staticmethod
    def create_skill(
        db: Session,
        skill_data: SkillCreate,
    ) -> Skill:
        skill = Skill(
            skill_id=skill_data.skill_id,
            name=skill_data.name,
            category=skill_data.category,
            description=skill_data.description,
        )

        db.add(skill)
        db.commit()
        db.refresh(skill)

        return skill

    @staticmethod
    def get_skill_by_id(
        db: Session,
        skill_id: int,
    ) -> Skill | None:
        stmt = select(Skill).where(Skill.id == skill_id)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_skill_by_code(
        db: Session,
        skill_code: str,
    ) -> Skill | None:
        stmt = select(Skill).where(Skill.skill_id == skill_code)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_all_skills(
        db: Session,
        category: str | None = None,
        is_active: bool | None = None,
    ) -> list[Skill]:
        stmt = select(Skill)
        if category:
            stmt = stmt.where(Skill.category == category)
        if is_active is not None:
            stmt = stmt.where(Skill.is_active == is_active)
        stmt = stmt.order_by(Skill.name)
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def update_skill(
        db: Session,
        skill_id: int,
        skill_data: SkillUpdate,
    ) -> Skill | None:
        skill = SkillService.get_skill_by_id(db, skill_id=skill_id)
        if not skill:
            return None

        update_data = skill_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(skill, field, value)

        db.commit()
        db.refresh(skill)
        return skill

    @staticmethod
    def delete_skill(
        db: Session,
        skill_id: int,
    ) -> bool:
        skill = SkillService.get_skill_by_id(db, skill_id=skill_id)
        if not skill:
            return False

        db.delete(skill)
        db.commit()
        return True
