from typing import Any, List
try:
    from fastapi import APIRouter, Depends, status
except ImportError:
    class APIRouter:
        def __init__(self, *args, **kwargs):
            self.routes = []
        def post(self, path, **kwargs):
            def decorator(func):
                self.routes.append(("POST", path, func))
                return func
            return decorator
        def get(self, path, **kwargs):
            def decorator(func):
                self.routes.append(("GET", path, func))
                return func
            return decorator

    def Depends(dep):
        return dep

    class status:
        HTTP_200_OK = 200
        HTTP_201_CREATED = 201

from ..db.session import get_db
from ..schemas.schemas import JobCreateSchema, JobResponseSchema
from ..services.ml_adapter import MLAdapter, get_ml_adapter
from ..services.job_service import JobService
from ..auth.rbac import require_role, get_current_user, CurrentUser

router = APIRouter()

@router.post(
    "/",
    response_model=JobResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new job posting with automatic skill extraction"
)
def create_job_posting(
    job_in: JobCreateSchema,
    db: Any = Depends(get_db),
    ml_adapter: MLAdapter = Depends(get_ml_adapter),
    _user: CurrentUser = Depends(require_role(["Employer", "Admin"]))
) -> JobResponseSchema:
    actual_db = db
    if hasattr(db, "__next__") or (isinstance(db, type(get_db())) and hasattr(db, "send")):
        actual_db = next(db)
    elif hasattr(db, "dependency"):
        actual_db = next(get_db())
    actual_adapter = ml_adapter if not hasattr(ml_adapter, "dependency") else get_ml_adapter()
    return JobService.create_job(db=actual_db, job_in=job_in, ml_adapter=actual_adapter)

@router.get(
    "/",
    response_model=List[JobResponseSchema],
    status_code=status.HTTP_200_OK,
    summary="List all job postings"
)
def list_job_postings(
    db: Any = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user)
) -> List[JobResponseSchema]:
    actual_db = db
    if hasattr(db, "__next__") or (isinstance(db, type(get_db())) and hasattr(db, "send")):
        actual_db = next(db)
    elif hasattr(db, "dependency"):
        actual_db = next(get_db())
    if hasattr(actual_db, "job_postings"):
        postings = list(actual_db.job_postings.values())
        return [
            JobResponseSchema(
                id=p.id,
                title=p.title,
                company=p.company,
                location=p.location,
                description=p.description,
                employer_id=p.employer_id,
                extracted_skills=[],
                created_at=p.created_at
            )
            for p in postings
        ]
    return []
