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
        HTTP_201_CREATED = 201

from ..db.session import get_db
from ..schemas.schemas import JobCreateSchema, JobResponseSchema
from ..services.ml_adapter import MLAdapter, get_ml_adapter
from ..services.job_service import JobService
from ..auth.rbac import require_role

router = APIRouter()

@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new job posting with automatic skill extraction"
)
def create_job_posting(
    job_in: JobCreateSchema,
    db = None,
    ml_adapter: MLAdapter = None,
    _user = None
):
    actual_db = db or next(get_db())
    actual_adapter = ml_adapter or get_ml_adapter()
    return JobService.create_job(db=actual_db, job_in=job_in, ml_adapter=actual_adapter)
