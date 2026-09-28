import unittest
from uuid import uuid4
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.schemas.user import UserCreate
from app.schemas.schemas import StudentSkillEvidenceCreateSchema, JobCreateSchema
from app.models.entities import StudentSkillEvidence

class TestPhase10ProductionReadiness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        from app.db.session import SessionLocal, _global_session
        from app.models.entities import Employer, User
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == 42).first()
            if not user:
                user = User(id=42, email="enterprise42@worknexus.io", hashed_password="fake", role="employer", full_name="Enterprise Recruiter")
                db.add(user)
                db.commit()
            emp = db.query(Employer).filter(Employer.id == 42).first()
            if not emp:
                db.add(Employer(id=42, company_name="Enterprise Cloud", user_id=42, trust_weight=1.0))
                db.commit()
            try:
                from sqlalchemy import text
                db.execute(text("SELECT setval(pg_get_serial_sequence('users', 'id'), (SELECT COALESCE(MAX(id), 1) FROM users));"))
                db.execute(text("SELECT setval(pg_get_serial_sequence('employers', 'id'), (SELECT COALESCE(MAX(id), 1) FROM employers));"))
                db.commit()
            except Exception:
                pass

    def test_01_admin_registration_rejected_prevents_privilege_escalation(self):
        """Verify that self-registration as admin is strictly blocked by schema validation."""
        with self.assertRaises(ValidationError) as ctx:
            UserCreate(
                email=f"hacker_{uuid4().hex[:6]}@malicious.org",
                password="Password123!",
                full_name="Attacker",
                role="admin"
            )
        self.assertIn("Admin accounts cannot be self-registered", str(ctx.exception))

    def test_02_job_create_schema_aliases_and_normalization(self):
        """Verify JobCreateSchema accepts job_title, company_name, comments, required_skills."""
        payload = {
            "job_title": "Lead ML Platform Engineer",
            "company_name": "Antigravity Systems",
            "location": "Bengaluru / Hybrid",
            "comments": "Looking for deep expertise in PyTorch and Kubernetes.",
            "required_skills": ["SKILL_PYTHON", "SKILL_DOCKER", "SKILL_KUBERNETES"]
        }
        schema = JobCreateSchema(**payload)
        self.assertEqual(schema.title, "Lead ML Platform Engineer")
        self.assertEqual(schema.company, "Antigravity Systems")
        self.assertIn("PyTorch and Kubernetes", schema.description)
        self.assertIn("Required Skills: SKILL_PYTHON", schema.description)

    def test_03_student_evidence_schema_normalization(self):
        """Verify StudentSkillEvidenceCreateSchema normalizes aliases and numeric strength."""
        # github_pr -> project, strength 8 -> advanced
        ev1 = StudentSkillEvidenceCreateSchema(
            skill_id="SKILL_PYTHON",
            evidence_type="github_pr",
            strength=8,
            metadata={"repo": "https://github.com/org/repo/pull/42"}
        )
        self.assertEqual(ev1.evidence_type, "project")
        self.assertEqual(ev1.strength, "advanced")

        # coursework -> course_completed, strength 5 -> intermediate
        ev2 = StudentSkillEvidenceCreateSchema(
            skill_id="SKILL_SQL",
            evidence_type="coursework",
            strength=5
        )
        self.assertEqual(ev2.evidence_type, "course_completed")
        self.assertEqual(ev2.strength, "intermediate")

    def test_04_student_profile_auto_provisioning_on_registration(self):
        """Verify that a registered student automatically receives a profile and ML endpoints work."""
        rand_hex = uuid4().hex[:6]
        email = f"student_{rand_hex}@worknexus.org"
        reg_res = self.client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "SecurePassword123!",
            "full_name": f"Student {rand_hex}",
            "role": "student"
        })
        self.assertEqual(reg_res.status_code, 201)
        user_id = reg_res.json()["id"]

        # Login
        login_res = self.client.post("/api/v1/auth/login", json={
            "email": email,
            "password": "SecurePassword123!"
        })
        self.assertEqual(login_res.status_code, 200)
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}", "X-User-Role": "Student", "X-User-Id": str(user_id)}

        # Fetch profile immediately — must NOT be 404
        prof_res = self.client.get(f"/api/v1/students/{user_id}/profile", headers=headers)
        self.assertEqual(prof_res.status_code, 200)
        prof_data = prof_res.json()
        self.assertEqual(prof_data["user_id"], user_id)
        self.assertIsNotNone(prof_data.get("target_role_id"))

    def test_05_employer_idor_protection_on_job_creation(self):
        """Verify employer_id is bound to authenticated user and cannot be spoofed."""
        # Fake header claiming Employer ID 42
        headers = {"X-User-Role": "Employer", "X-User-Id": "42"}
        job_payload = {
            "title": "Principal Architect",
            "company": "Enterprise Cloud",
            "location": "Remote",
            "description": "Enterprise cloud architecture with AWS and Python.",
            "employer_id": 9999 # Malicious attempt to post on behalf of employer 9999
        }
        res = self.client.post("/api/v1/jobs/", json=job_payload, headers=headers)
        self.assertEqual(res.status_code, 201)
        created_job = res.json()
        # Verify the employer_id was securely overridden to the authenticated user's ID
        self.assertEqual(created_job["employer_id"], 42)

    def test_06_student_gap_endpoint_response_structure(self):
        """Verify student gap endpoint returns enriched structure with matching metrics."""
        headers = {"X-User-Role": "Student", "X-User-Id": "1"}
        res = self.client.get("/api/v1/ml/students/STU_001/gap/ROLE_DATA_ENGINEER?mode=benchmark", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("overall_match_score", data)
        self.assertIn("gap_percentage", data)
        self.assertIn("skills_acquired", data)
        self.assertIn("skills_missing", data)
        self.assertIsInstance(data["skills_acquired"], list)
        self.assertIsInstance(data["skills_missing"], list)
