import unittest
from typing import Dict, Any, Optional

try:
    from fastapi.testclient import TestClient
    from fastapi import HTTPException
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    from app.services.ml_adapter import HTTPException

from app.main import app
from app.db.session import MockDatabaseSession, _global_session
from app.models.entities import Employer, User, JobPosting, JobSkill
from app.schemas.schemas import (
    SkillExtractionRequest,
    JobCreateSchema,
    EmployerFeedbackCreateSchema
)
from app.auth.rbac import CurrentUser, require_role, get_current_user
from app.api.routes_jobs import create_job_posting
from app.api.routes_employers import submit_employer_feedback
from app.api.routes_ml import (
    extract_skills_endpoint,
    get_demand_endpoint,
    get_course_gaps_endpoint,
    get_evidence_endpoint,
    get_recommendations_endpoint,
    get_role_context_endpoint,
    get_student_profile_endpoint
)

class TestResponse:
    def __init__(self, status_code: int, data: Any):
        self.status_code = status_code
        self._data = data

    def json(self) -> Dict[str, Any]:
        if hasattr(self._data, "dict"):
            return self._data.dict()
        if hasattr(self._data, "__dict__"):
            res = {}
            for k, v in self._data.__dict__.items():
                if isinstance(v, list):
                    res[k] = [item.dict() if hasattr(item, "dict") else (item.__dict__ if hasattr(item, "__dict__") else item) for item in v]
                else:
                    res[k] = v
            return res
        return self._data

class MockClient:
    def __init__(self, app):
        self.app = app
        self.db = _global_session

    def get(self, path: str, headers: Optional[Dict[str, str]] = None) -> TestResponse:
        headers = headers or {}
        user_role = headers.get("X-User-Role", "Employer")
        user_id = int(headers.get("X-User-Id", "1"))
        current_user = CurrentUser(user_id=user_id, email="user@worknexus.org", role=user_role)

        # Parse query params if any
        base_path = path.split("?")[0]
        params = {}
        if "?" in path:
            query_str = path.split("?")[1]
            for part in query_str.split("&"):
                if "=" in part:
                    k, v = part.split("=", 1)
                    params[k] = v

        mode = params.get("mode", "live")

        try:
            if base_path == "/health":
                return TestResponse(200, {"status": "healthy", "service": "worknexus-backend"})
            elif base_path == "/api/v1/ml/demand":
                res = get_demand_endpoint(mode=mode, db=self.db, _user=current_user)
                return TestResponse(200, res)
            elif base_path == "/api/v1/ml/course-gaps":
                res = get_course_gaps_endpoint(mode=mode, db=self.db, _user=current_user)
                return TestResponse(200, res)
            elif base_path == "/api/v1/ml/evidence":
                res = get_evidence_endpoint(mode=mode, db=self.db, _user=current_user)
                return TestResponse(200, res)
            elif base_path == "/api/v1/ml/recommendations":
                res = get_recommendations_endpoint(mode=mode, db=self.db, _user=current_user)
                return TestResponse(200, res)
            elif base_path.startswith("/api/v1/ml/roles/"):
                role_id = base_path.split("/")[-1]
                res = get_role_context_endpoint(role_id=role_id, mode=mode, db=self.db, _user=current_user)
                return TestResponse(200, res)
            elif "/profile" in base_path:
                student_id = base_path.split("/")[-2]
                res = get_student_profile_endpoint(student_id=student_id, mode=mode, db=self.db, _user=current_user)
                return TestResponse(200, res)

            return TestResponse(404, {"detail": "Not Found"})
        except HTTPException as e:
            return TestResponse(e.status_code, {"detail": e.detail})

    def post(self, path: str, json: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> TestResponse:
        headers = headers or {}
        user_role = headers.get("X-User-Role", "Employer")
        user_id = int(headers.get("X-User-Id", "1"))
        current_user = CurrentUser(user_id=user_id, email="user@worknexus.org", role=user_role)

        try:
            if path == "/api/v1/ml/extract-skills":
                req = SkillExtractionRequest(**(json or {}))
                res = extract_skills_endpoint(request=req, _user=current_user)
                return TestResponse(200, res)

            elif path == "/api/v1/jobs/":
                # Check RBAC
                check_role = require_role(["Employer", "Admin"])
                check_role(current_user)
                req = JobCreateSchema(**(json or {}))
                res = create_job_posting(job_in=req, db=self.db, _user=current_user)
                return TestResponse(201, res)

            elif path == "/api/v1/employers/feedback":
                # Check RBAC
                check_role = require_role(["Employer", "Admin"])
                check_role(current_user)
                req = EmployerFeedbackCreateSchema(**(json or {}))
                res = submit_employer_feedback(feedback_in=req, db=self.db, _user=current_user)
                return TestResponse(201, res)

            return TestResponse(404, {"detail": "Not Found"})
        except HTTPException as e:
            return TestResponse(e.status_code, {"detail": e.detail})

class TestBackendRoutes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db = _global_session
        if not cls.db.query(Employer).filter(lambda e: e.id == 1).first():
            cls.db.add(Employer(id=1, company_name="Main EV Corp", trust_weight=1.0))
        if FASTAPI_AVAILABLE:
            cls.client = TestClient(app)
        else:
            cls.client = MockClient(app)

    def test_01_health_check(self):
        """Test health endpoint."""
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "healthy", "service": "worknexus-backend"})

    def test_02_extract_skills_endpoint(self):
        """Test direct ML extraction proxy route."""
        payload = {"text": "Expert in Python, SQL, and Docker."}
        headers = {"X-User-Id": "1", "X-User-Role": "Student"}
        res = self.client.post("/api/v1/ml/extract-skills", json=payload, headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("skills", data)
        skill_ids = {s["skill_id"] for s in data["skills"]}
        self.assertIn("SK_PYTHON", skill_ids)
        self.assertIn("SK_SQL", skill_ids)
        self.assertIn("SK_DOCKER", skill_ids)

    def test_03_create_job_authorized_employer(self):
        """Test job creation route with authorized Employer role."""
        payload = {
            "title": "Backend Python Developer",
            "company": "Nexus Systems",
            "location": "Pune",
            "description": "Requires FastAPI, SQL, and Docker containerization.",
            "employer_id": 1
        }
        headers = {"X-User-Id": "1", "X-User-Role": "Employer"}
        res = self.client.post("/api/v1/jobs/", json=payload, headers=headers)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["title"], "Backend Python Developer")
        extracted = {s["skill_id"] for s in data["extracted_skills"]}
        self.assertIn("SK_FASTAPI", extracted)
        self.assertIn("SK_SQL", extracted)
        self.assertIn("SK_DOCKER", extracted)

    def test_04_create_job_forbidden_student(self):
        """Test job creation route blocks Student role with 403 Forbidden."""
        payload = {
            "title": "Unauthorized Job",
            "company": "Fake",
            "location": "Remote",
            "description": "Python"
        }
        headers = {"X-User-Id": "2", "X-User-Role": "Student"}
        res = self.client.post("/api/v1/jobs/", json=payload, headers=headers)
        self.assertEqual(res.status_code, 403)

    def test_05_submit_employer_feedback_authorized(self):
        """Test employer feedback submission with Employer role."""
        payload = {
            "employer_id": 1,
            "course_id": 101,
            "comments": "Great work on Python programming and Git version control.",
            "rating": 5
        }
        headers = {"X-User-Id": "1", "X-User-Role": "Employer"}
        res = self.client.post("/api/v1/employers/feedback", json=payload, headers=headers)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["employer_id"], 1)
        signals = {s["skill_id"] for s in data["signals"]}
        self.assertIn("SK_PYTHON", signals)
        self.assertIn("SK_GIT", signals)

    def test_06_submit_employer_feedback_forbidden_student(self):
        """Test employer feedback blocks Student role with 403 Forbidden."""
        payload = {
            "employer_id": 1,
            "comments": "Python",
            "rating": 5
        }
        headers = {"X-User-Id": "2", "X-User-Role": "Student"}
        res = self.client.post("/api/v1/employers/feedback", json=payload, headers=headers)
        self.assertEqual(res.status_code, 403)

    def test_07_get_demand_live(self):
        """Test GET /api/v1/ml/demand in live mode."""
        headers = {"X-User-Id": "1", "X-User-Role": "Student"}
        res = self.client.get("/api/v1/ml/demand?mode=live", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_jobs_analyzed", data)
        self.assertFalse(data.get("is_synthetic_artifact", True))

    def test_08_get_demand_benchmark(self):
        """Test GET /api/v1/ml/demand in benchmark mode."""
        headers = {"X-User-Id": "1", "X-User-Role": "Student"}
        res = self.client.get("/api/v1/ml/demand?mode=benchmark", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total_jobs_analyzed"], 295)
        self.assertTrue(data.get("is_synthetic_artifact", False))

    def test_09_get_course_gaps_live(self):
        """Test GET /api/v1/ml/course-gaps in live mode."""
        headers = {"X-User-Id": "1", "X-User-Role": "Student"}
        res = self.client.get("/api/v1/ml/course-gaps?mode=live", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("course_gaps", data)
        self.assertFalse(data.get("is_synthetic_artifact", True))

    def test_10_get_recommendations_live(self):
        """Test GET /api/v1/ml/recommendations in live mode."""
        headers = {"X-User-Id": "1", "X-User-Role": "Student"}
        res = self.client.get("/api/v1/ml/recommendations?mode=live", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("recommended_skills", data)
        self.assertFalse(data.get("is_synthetic_artifact", True))

if __name__ == "__main__":
    unittest.main()
