from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.schemas.job_skills import JobSkillCreate, JobSkillResponse
from app.services.job_posting_service import JobPostingService
from app.services.job_skill_service import JobSkillService
from app.services.skill_service import SkillService

router = APIRouter(
    prefix="/job-skills",
    tags=["Job Skills"],
)


@router.get(
    "",
    response_model=list[JobSkillResponse],
    summary="List job skill mappings",
)
@router.get(
    "/",
    response_model=list[JobSkillResponse],
    include_in_schema=False,
)
def get_job_skills(
    job_id: int | None = None,
    skill_id: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    return JobSkillService.get_all_job_skills(
        db=db,
        job_id=job_id,
        skill_id=skill_id,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{job_skill_id}",
    response_model=JobSkillResponse,
    summary="Get job skill mapping by ID",
)
def get_job_skill(
    job_skill_id: int,
    db: Session = Depends(get_db),
):
    job_skill = JobSkillService.get_job_skill(db=db, job_skill_id=job_skill_id)
    if not job_skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job skill mapping not found",
        )
    return job_skill


@router.post(
    "",
    response_model=JobSkillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Map a skill to a job posting",
)
@router.post(
    "/",
    response_model=JobSkillResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_job_skill(
    job_skill_data: JobSkillCreate,
    db: Session = Depends(get_db),
):
    # Verify job posting exists
    job_posting = JobPostingService.get_job_posting(db=db, job_id=job_skill_data.job_id)
    if not job_posting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job posting with id {job_skill_data.job_id} not found",
        )

    # Verify skill exists
    skill = SkillService.get_skill_by_code(db=db, skill_code=job_skill_data.skill_id)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill with skill_id '{job_skill_data.skill_id}' not found",
        )

    # Check for duplicate mapping
    existing = JobSkillService.get_job_skill_by_job_and_skill(
        db=db,
        job_id=job_skill_data.job_id,
        skill_id=job_skill_data.skill_id,
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skill is already mapped to this job posting",
        )

    return JobSkillService.create_job_skill(db=db, job_skill_data=job_skill_data)


@router.delete(
    "/{job_skill_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a job skill mapping",
)
def delete_job_skill(
    job_skill_id: int,
    db: Session = Depends(get_db),
):
    deleted = JobSkillService.delete_job_skill(db=db, job_skill_id=job_skill_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job skill mapping not found",
        )
    return {"message": "Job skill mapping deleted successfully"}
