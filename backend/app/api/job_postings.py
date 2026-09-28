from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.schemas.job_postings import JobPostingCreate, JobPostingResponse
from app.services.job_posting_service import JobPostingService
from app.services.employer_service import EmployerService
from app.auth.rbac import require_role, CurrentUser

router = APIRouter(
    prefix="/job-postings",
    tags=["Job Postings"],
)


@router.get(
    "",
    response_model=list[JobPostingResponse],
    summary="List all job postings",
)
@router.get(
    "/",
    response_model=list[JobPostingResponse],
    include_in_schema=False,
)
def get_job_postings(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    return JobPostingService.get_all_job_postings(db=db, skip=skip, limit=limit)


@router.get(
    "/{job_id}",
    response_model=JobPostingResponse,
    summary="Get job posting by ID",
)
def get_job_posting(
    job_id: int,
    db: Session = Depends(get_db),
):
    job_posting = JobPostingService.get_job_posting(db=db, job_id=job_id)
    if not job_posting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job posting not found",
        )
    return job_posting


@router.post(
    "",
    response_model=JobPostingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new job posting",
)
@router.post(
    "/",
    response_model=JobPostingResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_job_posting(
    job_data: JobPostingCreate,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role(["Employer", "Admin"])),
):
    return JobPostingService.create_job_posting(db=db, job_data=job_data)


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a job posting",
)
def delete_job_posting(
    job_id: int,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role(["Employer", "Admin"])),
):
    actual_db = next(db) if hasattr(db, "__next__") else db
    job = JobPostingService.get_job_posting(db=actual_db, job_id=job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job posting not found",
        )

    user_role = getattr(_user, "role", "").lower()
    if user_role == "employer":
        employer = EmployerService.get_employer_by_user_id(actual_db, _user.user_id)
        if not employer or job.employer_id != employer.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this job posting",
            )

    JobPostingService.delete_job_posting(db=actual_db, job_id=job_id)
    return {"message": "Job posting deleted successfully"}
