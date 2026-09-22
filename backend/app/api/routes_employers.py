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
from ..schemas.schemas import EmployerFeedbackCreateSchema, EmployerFeedbackResponseSchema
from ..services.ml_adapter import MLAdapter, get_ml_adapter
from ..services.employer_service import EmployerService
from ..auth.rbac import require_role, get_current_user, CurrentUser

router = APIRouter()

@router.post(
    "/feedback",
    response_model=EmployerFeedbackResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Submit structured employer feedback with automated skill intelligence"
)
def submit_employer_feedback(
    feedback_in: EmployerFeedbackCreateSchema,
    db: Any = Depends(get_db),
    ml_adapter: MLAdapter = Depends(get_ml_adapter),
    _user: CurrentUser = Depends(require_role(["Employer", "Admin"]))
) -> EmployerFeedbackResponseSchema:
    actual_db = db
    if hasattr(db, "__next__") or (isinstance(db, type(get_db())) and hasattr(db, "send")):
        actual_db = next(db)
    elif hasattr(db, "dependency"):
        actual_db = next(get_db())
    actual_adapter = ml_adapter if not hasattr(ml_adapter, "dependency") else get_ml_adapter()
    return EmployerService.submit_feedback(db=actual_db, feedback_in=feedback_in, ml_adapter=actual_adapter)

@router.get(
    "/feedback",
    response_model=List[EmployerFeedbackResponseSchema],
    status_code=status.HTTP_200_OK,
    summary="List submitted employer feedbacks"
)
def list_employer_feedback(
    db: Any = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user)
) -> List[EmployerFeedbackResponseSchema]:
    actual_db = db
    if hasattr(db, "__next__") or (isinstance(db, type(get_db())) and hasattr(db, "send")):
        actual_db = next(db)
    elif hasattr(db, "dependency"):
        actual_db = next(get_db())
    if hasattr(actual_db, "employer_feedback"):
        feedbacks = list(actual_db.employer_feedback.values())
        return [
            EmployerFeedbackResponseSchema(
                id=fb.id,
                employer_id=fb.employer_id,
                course_id=fb.course_id,
                comments=fb.comments,
                rating=fb.rating,
                detected_signals=[],
                created_at=fb.created_at
            )
            for fb in feedbacks
        ]
    return []
