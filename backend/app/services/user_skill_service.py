from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user_skills import UserSkill
from app.schemas.user_skill import UserSkillCreate, UserSkillUpdate


class UserSkillService:

    @staticmethod
    def add_user_skill(
        db: Session,
        user_id: int,
        skill_data: UserSkillCreate,
    ) -> UserSkill:
        user_skill = UserSkill(
            user_id=user_id,
            skill_id=skill_data.skill_id,
            proficiency_level=skill_data.proficiency_level,
            source=skill_data.source,
        )
        db.add(user_skill)
        db.commit()
        db.refresh(user_skill)
        return user_skill

    @staticmethod
    def get_user_skills(
        db: Session,
        user_id: int,
    ) -> list[UserSkill]:
        stmt = select(UserSkill).where(UserSkill.user_id == user_id).order_by(UserSkill.created_at.desc())
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def get_user_skill_by_id(
        db: Session,
        id: int,
    ) -> UserSkill | None:
        stmt = select(UserSkill).where(UserSkill.id == id)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_user_skill_by_user_and_skill(
        db: Session,
        user_id: int,
        skill_id: int,
    ) -> UserSkill | None:
        stmt = select(UserSkill).where(
            UserSkill.user_id == user_id,
            UserSkill.skill_id == skill_id,
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def update_user_skill(
        db: Session,
        id: int,
        data: UserSkillUpdate,
    ) -> UserSkill | None:
        user_skill = UserSkillService.get_user_skill_by_id(db, id=id)
        if not user_skill:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user_skill, field, value)

        db.commit()
        db.refresh(user_skill)
        return user_skill

    @staticmethod
    def delete_user_skill(
        db: Session,
        id: int,
    ) -> bool:
        user_skill = UserSkillService.get_user_skill_by_id(db, id=id)
        if not user_skill:
            return False

        db.delete(user_skill)
        db.commit()
        return True
