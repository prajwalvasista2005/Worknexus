from typing import List, Optional
from ..models.entities import JobPosting, JobSkill
from ..schemas.schemas import JobCreateSchema, JobResponseSchema, SkillExtractionItem
from .ml_adapter import MLAdapter

class JobService:

    @staticmethod
    def create_job(db, job_in: JobCreateSchema, ml_adapter: MLAdapter) -> JobResponseSchema:
        # 1. Create JobPosting entity
        job = JobPosting(
            id=None,
            title=job_in.title,
            company=job_in.company,
            location=job_in.location,
            description=job_in.description,
            employer_id=job_in.employer_id
        )
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
                id=None,
                job_id=job.id,
                skill_id=sk_id,
                confidence_score=conf
            )
            db.add(job_skill)
            extracted_items.append(SkillExtractionItem(skill_id=sk_id, confidence_score=conf))

        db.commit()
        db.refresh(job)

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
