from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_postings import JobPosting
from app.schemas.job_postings import JobPostingCreate


class JobPostingService:

    @staticmethod
    def create_job_posting(
        db: Session,
        job_data: JobPostingCreate,
    ) -> JobPosting:
        job_posting = JobPosting(
            title=job_data.title,
            company_name=job_data.company_name,
            description=job_data.description,
            location=job_data.location,
            source=job_data.source,
            posted_date=job_data.posted_date,
        )
        db.add(job_posting)
        db.commit()
        db.refresh(job_posting)
        return job_posting

    @staticmethod
    def get_job_posting(
        db: Session,
        job_id: int,
    ) -> JobPosting | None:
        stmt = select(JobPosting).where(JobPosting.id == job_id)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_all_job_postings(
        db: Session,
        skip: int = 0,
        limit: int = 100,
    ) -> list[JobPosting]:
        stmt = (
            select(JobPosting)
            .order_by(JobPosting.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def delete_job_posting(
        db: Session,
        job_id: int,
    ) -> bool:
        job_posting = JobPostingService.get_job_posting(db, job_id=job_id)
        if not job_posting:
            return False

        db.delete(job_posting)
        db.commit()
        return True


# Standalone function aliases matching task specifications
create_job_posting = JobPostingService.create_job_posting
get_job_posting = JobPostingService.get_job_posting
get_all_job_postings = JobPostingService.get_all_job_postings
delete_job_posting = JobPostingService.delete_job_posting
