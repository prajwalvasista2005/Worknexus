from typing import List, Optional
from ..models.employers import Employer
from ..models.job_postings import JobPosting
from ..models.jobSkill import JobSkill
from ..schemas.schemas import JobCreateSchema, JobResponseSchema, SkillExtractionItem
from .ml_adapter import MLAdapter

class JobService:

    @staticmethod
    def create_job(db, job_in: JobCreateSchema, ml_adapter: MLAdapter) -> JobResponseSchema:
        from fastapi import HTTPException
        from sqlalchemy.exc import IntegrityError
        from .employer_service import EmployerService

        emp_id = job_in.employer_id
        if emp_id is not None:
            emp = EmployerService.get_employer_by_id(db, emp_id)
            if not emp:
                raise HTTPException(
                    status_code=404,
                    detail=f"Employer with ID {emp_id} does not exist in employers table."
                )

        job = JobPosting(
            title=job_in.title,
            company_name=job_in.company,
            location=job_in.location,
            description=job_in.description,
            employer_id=emp_id,
            source=f"employer_{emp_id}" if emp_id else "direct"
        )

        try:
            db.add(job)
            db.flush()

            # 2. Invoke ML Engine via MLAdapter
            ml_result = ml_adapter.process_job({
                "id": str(job.id),
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "description": job.description
            })

            # 3. Persist extracted skills mapped to canonical taxonomy
            extracted_items: List[SkillExtractionItem] = []
            for s in ml_result.extracted_skills:
                sk_id = s["skill_id"]
                conf = float(s["confidence_score"])
                
                job_skill = JobSkill(
                    job_id=job.id,
                    skill_id=sk_id,
                    confidence_score=conf
                )
                db.add(job_skill)
                extracted_items.append(SkillExtractionItem(skill_id=sk_id, confidence_score=conf))

            db.commit()
            try:
                db.refresh(job)
            except Exception:
                pass

        except HTTPException:
            if hasattr(db, "rollback"):
                db.rollback()
            raise
        except IntegrityError as ie:
            if hasattr(db, "rollback"):
                db.rollback()
            orig_msg = str(ie.orig) if hasattr(ie, "orig") else str(ie)
            raise HTTPException(
                status_code=400,
                detail=f"Database integrity error: {orig_msg}"
            )
        except Exception as e:
            if hasattr(db, "rollback"):
                db.rollback()
            raise

        return JobResponseSchema(
            id=job.id,
            title=job.title,
            company=job.company,
            location=job.location,
            description=job.description,
            employer_id=job.employer_id,
            extracted_skills=extracted_items,
            created_at=job.created_at
        )
