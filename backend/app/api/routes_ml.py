try:
    from fastapi import APIRouter, Depends, status, Query
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

    def Query(default, **kwargs):
        return default

    class status:
        HTTP_200_OK = 200

from ..db.session import get_db
from ..schemas.schemas import SkillExtractionRequest, SkillExtractionResponse, SkillExtractionItem
from ..services.ml_adapter import MLAdapter, get_ml_adapter
from ..auth.rbac import get_current_user, CurrentUser

router = APIRouter()

@router.post(
    "/extract-skills",
    status_code=status.HTTP_200_OK,
    summary="Extract canonical skills from free-form text"
)
def extract_skills_endpoint(
    request: SkillExtractionRequest,
    ml_adapter: MLAdapter = None,
    _user: CurrentUser = None
):
    actual_adapter = ml_adapter or get_ml_adapter()
    results = actual_adapter.extract_skills(request.text)
    items = [
        SkillExtractionItem(
            skill_id=r["skill_id"],
            confidence_score=float(r["confidence_score"])
        )
        for r in results
    ]
    return SkillExtractionResponse(skills=items)

@router.get(
    "/demand",
    status_code=status.HTTP_200_OK,
    summary="Retrieve skill demand intelligence (live or benchmark)"
)
def get_demand_endpoint(
    mode: str = "live",
    db = None,
    ml_adapter: MLAdapter = None,
    _user: CurrentUser = None
):
    actual_db = db or next(get_db())
    actual_adapter = ml_adapter or get_ml_adapter()
    res = actual_adapter.get_skill_demand(db=actual_db, mode=mode)
    return res.to_dict()

@router.get(
    "/course-gaps",
    status_code=status.HTTP_200_OK,
    summary="Retrieve curriculum skill gap intelligence (live or benchmark)"
)
def get_course_gaps_endpoint(
    mode: str = "live",
    db = None,
    ml_adapter: MLAdapter = None,
    _user: CurrentUser = None
):
    actual_db = db or next(get_db())
    actual_adapter = ml_adapter or get_ml_adapter()
    res = actual_adapter.get_course_skill_gaps(db=actual_db, mode=mode)
    return res.to_dict()

@router.get(
    "/evidence",
    status_code=status.HTTP_200_OK,
    summary="Retrieve multi-signal evidence intelligence (live or benchmark)"
)
def get_evidence_endpoint(
    mode: str = "live",
    db = None,
    ml_adapter: MLAdapter = None,
    _user: CurrentUser = None
):
    actual_db = db or next(get_db())
    actual_adapter = ml_adapter or get_ml_adapter()
    res = actual_adapter.get_skill_evidence(db=actual_db, mode=mode)
    return res.to_dict()

@router.get(
    "/recommendations",
    status_code=status.HTTP_200_OK,
    summary="Retrieve generic skill recommendations (live or benchmark)"
)
def get_recommendations_endpoint(
    mode: str = "live",
    db = None,
    ml_adapter: MLAdapter = None,
    _user: CurrentUser = None
):
    actual_db = db or next(get_db())
    actual_adapter = ml_adapter or get_ml_adapter()
    res = actual_adapter.get_skill_recommendations(db=actual_db, mode=mode)
    return res.to_dict()

@router.get(
    "/roles/{role_id}",
    status_code=status.HTTP_200_OK,
    summary="Retrieve role contextual recommendations (live or benchmark)"
)
def get_role_context_endpoint(
    role_id: str,
    mode: str = "live",
    db = None,
    ml_adapter: MLAdapter = None,
    _user: CurrentUser = None
):
    actual_db = db or next(get_db())
    actual_adapter = ml_adapter or get_ml_adapter()
    res = actual_adapter.get_role_skill_context(role_id=role_id, db=actual_db, mode=mode)
    return res.to_dict()

@router.get(
    "/students/{student_id}/profile",
    status_code=status.HTTP_200_OK,
    summary="Retrieve student skill profile (live or benchmark)"
)
def get_student_profile_endpoint(
    student_id: str,
    mode: str = "live",
    db = None,
    ml_adapter: MLAdapter = None,
    _user: CurrentUser = None
):
    actual_db = db or next(get_db())
    actual_adapter = ml_adapter or get_ml_adapter()
    res = actual_adapter.get_student_skill_profile(student_id=student_id, db=actual_db, mode=mode)
    return res.to_dict()

@router.get(
    "/students/{student_id}/gap/{role_id}",
    status_code=status.HTTP_200_OK,
    summary="Retrieve student skill gap analysis (live or benchmark)"
)
def get_student_gap_endpoint(
    student_id: str,
    role_id: str,
    mode: str = "live",
    db = None,
    ml_adapter: MLAdapter = None,
    _user: CurrentUser = None
):
    actual_db = db or next(get_db())
    actual_adapter = ml_adapter or get_ml_adapter()
    res = actual_adapter.get_student_skill_gap(student_id=student_id, role_id=role_id, db=actual_db, mode=mode)
    return res.to_dict()

@router.get(
    "/students/{student_id}/recommendations/{role_id}",
    status_code=status.HTTP_200_OK,
    summary="Retrieve personalized skill recommendations (live or benchmark)"
)
def get_personalized_recommendations_endpoint(
    student_id: str,
    role_id: str,
    mode: str = "live",
    db = None,
    ml_adapter: MLAdapter = None,
    _user: CurrentUser = None
):
    actual_db = db or next(get_db())
    actual_adapter = ml_adapter or get_ml_adapter()
    res = actual_adapter.get_personalized_recommendations(student_id=student_id, role_id=role_id, db=actual_db, mode=mode)
    return res.to_dict()

@router.get(
    "/students/{student_id}/course-candidates/{role_id}",
    status_code=status.HTTP_200_OK,
    summary="Retrieve course candidate recommendations (live or benchmark)"
)
def get_course_candidates_endpoint(
    student_id: str,
    role_id: str,
    mode: str = "live",
    db = None,
    ml_adapter: MLAdapter = None,
    _user: CurrentUser = None
):
    actual_db = db or next(get_db())
    actual_adapter = ml_adapter or get_ml_adapter()
    res = actual_adapter.get_course_candidates(student_id=student_id, role_id=role_id, db=actual_db, mode=mode)
    return res.to_dict()
