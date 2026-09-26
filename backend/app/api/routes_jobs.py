from typing import List, Any
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.job_postings import JobPosting
from app.schemas.schemas import JobCreateSchema, JobResponseSchema
from app.services.ml_adapter import MLAdapter, get_ml_adapter
from app.services.job_service import JobService
from app.services.job_posting_service import JobPostingService
from app.services.employer_service import EmployerService
from app.auth.rbac import require_role, get_current_user, CurrentUser

router = APIRouter()


@router.post(
    "/",
    response_model=JobResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new job posting with automatic skill extraction"
)
def create_job_posting(
    job_in: JobCreateSchema,
    db: Session = Depends(get_db),
    ml_adapter: MLAdapter = Depends(get_ml_adapter),
    _user: CurrentUser = Depends(require_role(["Employer", "Admin"]))
) -> JobResponseSchema:
    actual_db = next(db) if hasattr(db, "__next__") else db
    actual_adapter = ml_adapter if not hasattr(ml_adapter, "dependency") else get_ml_adapter()

    user_role = getattr(_user, "role", "").lower() if _user else ""

    if user_role == "employer":
        # Resolve the authenticated employer user to their Employer profile record
        employer = EmployerService.get_employer_by_user_id(actual_db, _user.user_id)
        if not employer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employer profile not found for user {_user.user_id}. Please create an employer profile before posting jobs."
            )
        # Authoritatively assign employer.id (never write _user.user_id directly)
        job_in.employer_id = employer.id
    elif user_role == "admin":
        if job_in.employer_id is not None:
            employer = EmployerService.get_employer_by_id(actual_db, job_in.employer_id)
            if not employer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Employer with ID {job_in.employer_id} not found."
                )

    return JobService.create_job(db=actual_db, job_in=job_in, ml_adapter=actual_adapter)


@router.get(
    "/",
    response_model=List[JobResponseSchema],
    status_code=status.HTTP_200_OK,
    summary="List all job postings"
)
def list_job_postings(
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user)
) -> List[JobResponseSchema]:
    actual_db = next(db) if hasattr(db, "__next__") else db
    if hasattr(actual_db, "query"):
        postings = actual_db.query(JobPosting).order_by(JobPosting.id.desc()).all()
    elif hasattr(actual_db, "job_postings"):
        postings = list(actual_db.job_postings.values())
    else:
        postings = []

    return [
        JobResponseSchema(
            id=p.id,
            title=p.title,
            company=getattr(p, "company", getattr(p, "company_name", "")),
            location=p.location or "Remote",
            description=p.description,
            employer_id=getattr(p, "employer_id", None),
            extracted_skills=[],
            created_at=p.created_at
        )
        for p in postings
    ]


@router.get(
    "/{job_id}",
    response_model=JobResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Get single job posting by ID"
)
def get_job_posting_by_id(
    job_id: int,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user)
) -> JobResponseSchema:
    from fastapi import HTTPException
    actual_db = next(db) if hasattr(db, "__next__") else db
    job = JobPostingService.get_job_posting(db=actual_db, job_id=job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job posting not found")
    return JobResponseSchema(
        id=job.id,
        title=job.title,
        company=getattr(job, "company", getattr(job, "company_name", "")),
        location=job.location or "Remote",
        description=job.description,
        employer_id=getattr(job, "employer_id", None),
        extracted_skills=[],
        created_at=job.created_at
    )


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a job posting"
)
def delete_job_posting_by_id(
    job_id: int,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role(["Employer", "Admin"]))
):
    from fastapi import HTTPException
    actual_db = next(db) if hasattr(db, "__next__") else db
    deleted = JobPostingService.delete_job_posting(db=actual_db, job_id=job_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job posting not found")
    return {"message": "Job posting deleted successfully"}

