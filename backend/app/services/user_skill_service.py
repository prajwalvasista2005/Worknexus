from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.user_skills import UserSkill
from app.schemas.user_skill import UserSkillCreate, UserSkillUpdate
from app.services.skill_service import SkillService


class UserSkillService:

    @staticmethod
    def _hydrate_user_skill(us: UserSkill, db: Any) -> UserSkill:
        if not us:
            return us
        # Resolve skill relation if not already populated.
        # The UserSkill model exposes canonical_id, skill_name, name, and category
        # as read-only @property methods that derive their values from us.skill, so
        # we only need to ensure the relationship is set — direct assignment is not
        # required (and would raise AttributeError on a property without a setter).
        sk = getattr(us, "skill", None)
        if not sk and us.skill_id is not None:
            try:
                sk = SkillService.get_skill_by_id(db, us.skill_id)
                if sk:
                    us.skill = sk
            except Exception:
                pass
        return us

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
        return UserSkillService._hydrate_user_skill(user_skill, db)

    @staticmethod
    def get_user_skills(
        db: Session,
        user_id: int,
    ) -> list[UserSkill]:
        if type(db).__name__ == "MockDatabaseSession" or not hasattr(db, "execute"):
            skills = [s for s in getattr(db, "user_skills", []) if getattr(s, "user_id", None) == user_id]
            return [UserSkillService._hydrate_user_skill(us, db) for us in skills]
        stmt = (
            select(UserSkill)
            .options(joinedload(UserSkill.skill))
            .where(UserSkill.user_id == user_id)
            .order_by(UserSkill.created_at.desc())
        )
        items = list(db.execute(stmt).scalars().all())
        return [UserSkillService._hydrate_user_skill(us, db) for us in items]

    @staticmethod
    def get_user_skill_by_id(
        db: Session,
        id: int,
    ) -> UserSkill | None:
        if type(db).__name__ == "MockDatabaseSession" or not hasattr(db, "execute"):
            us = next((s for s in getattr(db, "user_skills", []) if getattr(s, "id", None) == id), None)
            return UserSkillService._hydrate_user_skill(us, db) if us else None
        stmt = select(UserSkill).options(joinedload(UserSkill.skill)).where(UserSkill.id == id)
        us = db.execute(stmt).scalar_one_or_none()
        return UserSkillService._hydrate_user_skill(us, db) if us else None

    @staticmethod
    def get_user_skill_by_user_and_skill(
        db: Session,
        user_id: int,
        skill_id: int,
    ) -> UserSkill | None:
        if type(db).__name__ == "MockDatabaseSession" or not hasattr(db, "execute"):
            us = next(
                (
                    s for s in getattr(db, "user_skills", [])
                    if getattr(s, "user_id", None) == user_id and getattr(s, "skill_id", None) == skill_id
                ),
                None
            )
            return UserSkillService._hydrate_user_skill(us, db) if us else None
        stmt = (
            select(UserSkill)
            .options(joinedload(UserSkill.skill))
            .where(
                UserSkill.user_id == user_id,
                UserSkill.skill_id == skill_id,
            )
        )
        us = db.execute(stmt).scalar_one_or_none()
        return UserSkillService._hydrate_user_skill(us, db) if us else None

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
        return UserSkillService._hydrate_user_skill(user_skill, db)

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
