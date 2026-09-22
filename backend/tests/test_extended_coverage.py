import unittest
from fastapi.testclient import TestClient
from app.main import app

class TestExtendedApiCoverage(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_root_and_health_endpoints(self):
        """Test root '/' and '/health' endpoints."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "healthy")

        res_health = self.client.get("/health")
        self.assertEqual(res_health.status_code, 200)
        self.assertEqual(res_health.json()["service"], "worknexus-backend")

    def test_02_list_job_postings_endpoint(self):
        """Test GET /api/v1/jobs/ endpoint."""
        res = self.client.get("/api/v1/jobs/", headers={"X-User-Role": "Employer", "X-User-Id": "1"})
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json(), list)

    def test_03_list_employer_feedback_endpoint(self):
        """Test GET /api/v1/employers/feedback endpoint."""
        res = self.client.get("/api/v1/employers/feedback", headers={"X-User-Role": "Employer", "X-User-Id": "1"})
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json(), list)

    def test_04_target_roles_lifecycle(self):
        """Test listing and creating target career roles."""
        # 1. List roles
        res = self.client.get("/api/v1/roles/", headers={"X-User-Role": "Student", "X-User-Id": "1"})
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json(), list)

        # 2. Create role as Admin
        new_role = {
            "id": "ROLE_AI_RESEARCHER",
            "name": "AI Research Scientist",
            "description": "Develops novel deep learning architectures and agents",
            "skill_ids": ["SK_PYTHON", "SK_DOCKER"]
        }
        create_res = self.client.post("/api/v1/roles/", json=new_role, headers={"X-User-Role": "Admin", "X-User-Id": "99"})
        self.assertEqual(create_res.status_code, 201)
        role_data = create_res.json()
        self.assertEqual(role_data["id"], "ROLE_AI_RESEARCHER")
        self.assertEqual(role_data["name"], "AI Research Scientist")

        # 3. Fetch specific role
        get_res = self.client.get("/api/v1/roles/ROLE_AI_RESEARCHER", headers={"X-User-Role": "Student", "X-User-Id": "1"})
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json()["name"], "AI Research Scientist")

    def test_05_target_role_create_forbidden_for_student(self):
        """Test that Student role cannot create new target career roles."""
        payload = {
            "id": "ROLE_UNAUTHORIZED",
            "name": "Unauthorized Role",
            "skill_ids": ["SK_PYTHON"]
        }
        res = self.client.post("/api/v1/roles/", json=payload, headers={"X-User-Role": "Student", "X-User-Id": "10"})
        self.assertEqual(res.status_code, 403)

    def test_06_student_evidence_and_profile_flow(self):
        """Test student evidence submission, retrieval, and profile check."""
        user_id = 1001
        evidence_payload = {
            "skill_id": "SK_PYTHON",
            "evidence_type": "project",
            "strength": "advanced",
            "metadata": {"repo": "worknexus-prototype", "score": 95}
        }
        # Submit evidence
        post_res = self.client.post(
            f"/api/v1/students/{user_id}/evidence",
            json=evidence_payload,
            headers={"X-User-Role": "Student", "X-User-Id": str(user_id)}
        )
        self.assertEqual(post_res.status_code, 201)
        evidence_data = post_res.json()
        self.assertEqual(evidence_data["skill_id"], "SK_PYTHON")

        # List evidence for user
        list_res = self.client.get(
            f"/api/v1/students/{user_id}/evidence",
            headers={"X-User-Role": "Student", "X-User-Id": str(user_id)}
        )
        self.assertEqual(list_res.status_code, 200)
        self.assertGreaterEqual(len(list_res.json()), 1)

        # Retrieve profile
        profile_res = self.client.get(
            f"/api/v1/students/{user_id}/profile",
            headers={"X-User-Role": "Student", "X-User-Id": str(user_id)}
        )
        self.assertEqual(profile_res.status_code, 200)
        self.assertEqual(profile_res.json()["user_id"], user_id)

    def test_07_student_cannot_view_other_student_evidence(self):
        """Test IDOR protection: Student 1002 cannot view Student 1001 evidence."""
        res = self.client.get(
            "/api/v1/students/1001/evidence",
            headers={"X-User-Role": "Student", "X-User-Id": "1002"}
        )
        self.assertEqual(res.status_code, 403)

    def test_08_ml_role_context_and_course_candidates(self):
        """Test ML diagnostic endpoints for role context and course candidates."""
        # 1. Role context
        role_res = self.client.get("/api/v1/ml/roles/ROLE_DATA_ENGINEER?mode=benchmark")
        self.assertEqual(role_res.status_code, 200)
        role_json = role_res.json()
        self.assertIn("role_id", role_json)

        # 2. Course candidates
        cand_res = self.client.get("/api/v1/ml/students/STU_001/course-candidates/ROLE_DATA_ENGINEER?mode=benchmark")
        self.assertEqual(cand_res.status_code, 200)
        cand_json = cand_res.json()
        self.assertIn("candidate_courses", cand_json)
