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
            # 1. Check if emp_id matches an existing Employer by primary key
            emp = EmployerService.get_employer_by_id(db, emp_id)
            if not emp:
                # 2. Check if emp_id is actually a user_id
                emp = EmployerService.get_employer_by_user_id(db, emp_id)
            if not emp:
                # 3. Defensive recovery: Try to auto-provision employer profile for this user
                emp = EmployerService.get_or_create_employer_by_user_id(
                    db,
                    user_id=emp_id,
                    company_name=job_in.company
                )

            if emp:
                emp_id = emp.id
                job_in.employer_id = emp.id
            else:
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
            from .skill_service import SkillService

            skills_to_process = []
            seen_raw_keys = set()

            for s in ml_result.extracted_skills:
                sk_code = s.get("skill_id") if isinstance(s, dict) else getattr(s, "skill_id", None)
                conf = float(s.get("confidence_score", 1.0)) if isinstance(s, dict) else float(getattr(s, "confidence_score", 1.0))
                if sk_code is not None:
                    k = str(sk_code).strip().lower()
                    if k and k not in seen_raw_keys:
                        seen_raw_keys.add(k)
                        skills_to_process.append((sk_code, conf))

            # Also incorporate any skills explicitly provided in job_in
            raw_input_skills = getattr(job_in, "skills", None) or getattr(job_in, "required_skills", None)
            if raw_input_skills:
                items = []
                if isinstance(raw_input_skills, str):
                    items = [x.strip() for x in raw_input_skills.split(",") if x.strip()]
                elif isinstance(raw_input_skills, list):
                    for elem in raw_input_skills:
                        if isinstance(elem, str):
                            items.extend([x.strip() for x in elem.split(",") if x.strip()])
                        elif isinstance(elem, dict) and "skill_id" in elem:
                            sk = elem["skill_id"]
                            c = float(elem.get("confidence_score", 1.0))
                            k = str(sk).strip().lower()
                            if k and k not in seen_raw_keys:
                                seen_raw_keys.add(k)
                                skills_to_process.append((sk, c))
                        elif isinstance(elem, int):
                            items.append(elem)
                for item in items:
                    k = str(item).strip().lower()
                    if k and k not in seen_raw_keys:
                        seen_raw_keys.add(k)
                        skills_to_process.append((item, 1.0))

            extracted_items: List[SkillExtractionItem] = []
            seen_db_skill_ids = set()

            for sk_raw, conf in skills_to_process:
                if not sk_raw:
                    continue
                # Resolve or upsert into skills table to get integer primary key
                resolved_id = SkillService.get_or_create_skill_id(db, sk_raw)
                if resolved_id is not None:
                    resolved_id = int(resolved_id)
                    if resolved_id not in seen_db_skill_ids:
                        seen_db_skill_ids.add(resolved_id)
                        job_skill = JobSkill(
                            job_id=job.id,
                            skill_id=resolved_id,
                            confidence_score=conf
                        )
                        db.add(job_skill)

                extracted_items.append(SkillExtractionItem(skill_id=sk_raw, confidence_score=conf))

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
            confidence_scores={s.skill_id: s.confidence_score for s in extracted_items} if extracted_items else None,
            skills=[s.skill_id for s in extracted_items] if extracted_items else None,
            created_at=job.created_at
        )
