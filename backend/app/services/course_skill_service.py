from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course_skills import CourseSkill
from app.schemas.course_skill import CourseSkillCreate


class CourseSkillService:

    @staticmethod
    def add_skill_to_course(
        db: Session,
        data: CourseSkillCreate,
    ) -> CourseSkill:
        course_skill = CourseSkill(
            course_id=data.course_id,
            skill_id=data.skill_id,
        )
        db.add(course_skill)
        db.commit()
        db.refresh(course_skill)
        return course_skill

    @staticmethod
    def get_course_skills(
        db: Session,
        course_id: int | None = None,
        skill_id: int | None = None,
    ) -> list[CourseSkill]:
        stmt = select(CourseSkill)
        if course_id is not None:
            stmt = stmt.where(CourseSkill.course_id == course_id)
        if skill_id is not None:
            stmt = stmt.where(CourseSkill.skill_id == skill_id)
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def get_course_skill_by_id(
        db: Session,
        id: int,
    ) -> CourseSkill | None:
        stmt = select(CourseSkill).where(CourseSkill.id == id)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_course_skill(
        db: Session,
        course_id: int,
        skill_id: int,
    ) -> CourseSkill | None:
        stmt = select(CourseSkill).where(
            CourseSkill.course_id == course_id,
            CourseSkill.skill_id == skill_id,
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def delete_course_skill(
        db: Session,
        id: int,
    ) -> bool:
        course_skill = CourseSkillService.get_course_skill_by_id(db, id=id)
        if not course_skill:
            return False

        db.delete(course_skill)
        db.commit()
        return True
