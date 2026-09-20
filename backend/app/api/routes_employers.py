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
from ..schemas.schemas import EmployerFeedbackCreateSchema, EmployerFeedbackResponseSchema
from ..services.ml_adapter import MLAdapter, get_ml_adapter
from ..services.employer_service import EmployerService
from ..auth.rbac import require_role

router = APIRouter()

@router.post(
    "/feedback",
    status_code=status.HTTP_201_CREATED,
    summary="Submit structured employer feedback with automated skill intelligence"
)
def submit_employer_feedback(
    feedback_in: EmployerFeedbackCreateSchema,
    db = None,
    ml_adapter: MLAdapter = None,
    _user = None
):
    actual_db = db or next(get_db())
    actual_adapter = ml_adapter or get_ml_adapter()
    return EmployerService.submit_feedback(db=actual_db, feedback_in=feedback_in, ml_adapter=actual_adapter)
