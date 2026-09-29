
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.jobSkill import JobSkill
from app.schemas.job_skills import JobSkillCreate


class JobSkillService:

    @staticmethod
    def create_job_skill(
        db: Session,
        job_skill_data: JobSkillCreate,
    ) -> JobSkill:
        resolved_skill_id = job_skill_data.skill_id
        if isinstance(resolved_skill_id, str):
            if resolved_skill_id.isdigit():
                resolved_skill_id = int(resolved_skill_id)
            else:
                from app.services.skill_service import SkillService
                sk = SkillService.get_skill_by_code(db, resolved_skill_id) or SkillService.get_skill_by_name(db, resolved_skill_id)
                if sk:
                    resolved_skill_id = sk.id
        job_skill = JobSkill(
            job_id=job_skill_data.job_id,
            skill_id=resolved_skill_id,
        )
        db.add(job_skill)
        db.commit()
        db.refresh(job_skill)
        return job_skill

    @staticmethod
    def get_job_skill(
        db: Session,
        job_skill_id: int,
    ) -> JobSkill | None:
        stmt = select(JobSkill).where(JobSkill.id == job_skill_id)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_job_skill_by_job_and_skill(
        db: Session,
        job_id: int,
        skill_id: int | str,
    ) -> JobSkill | None:
        stmt = select(JobSkill).where(
            JobSkill.job_id == job_id,
            JobSkill.skill_id == skill_id,
        )
        try:
            res = db.execute(stmt).scalar_one_or_none()
        except Exception:
            res = None

        if not res and isinstance(skill_id, str):
            from app.models.skills import Skill
            try:
                stmt2 = select(JobSkill).join(Skill, JobSkill.skill_id == Skill.id).where(
                    JobSkill.job_id == job_id,
                    Skill.skill_id == skill_id,
                )
                res = db.execute(stmt2).scalar_one_or_none()
            except Exception:
                pass
        return res

    @staticmethod
    def get_all_job_skills(
        db: Session,
        job_id: int | None = None,
        skill_id: int | str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[JobSkill]:
        stmt = select(JobSkill)
        if job_id is not None:
            stmt = stmt.where(JobSkill.job_id == job_id)
        if skill_id is not None:
            if isinstance(skill_id, int) or (isinstance(skill_id, str) and skill_id.isdigit()):
                stmt = stmt.where(JobSkill.skill_id == int(skill_id))
            else:
                from app.models.skills import Skill
                stmt = stmt.join(Skill, JobSkill.skill_id == Skill.id).where(Skill.skill_id == skill_id)
        stmt = stmt.order_by(JobSkill.id.desc()).offset(skip).limit(limit)
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def delete_job_skill(
        db: Session,
        job_skill_id: int,
    ) -> bool:
        job_skill = JobSkillService.get_job_skill(db, job_skill_id=job_skill_id)
        if not job_skill:
            return False

        db.delete(job_skill)
        db.commit()
        return True


# Standalone function aliases matching task specifications
create_job_skill = JobSkillService.create_job_skill
get_job_skill = JobSkillService.get_job_skill
get_all_job_skills = JobSkillService.get_all_job_skills
delete_job_skill = JobSkillService.delete_job_skill
get_job_skill_by_job_and_skill = JobSkillService.get_job_skill_by_job_and_skill
