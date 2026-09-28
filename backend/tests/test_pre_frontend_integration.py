import unittest
from fastapi.testclient import TestClient
from app.main import app

class TestPreFrontendIntegrationValidation(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        from app.db.session import SessionLocal, _global_session
        from app.models.entities import Employer, User
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == 50).first()
            if not user:
                user = User(id=50, email="recruiter50@tata.com", hashed_password="fake", role="employer", full_name="Tata Recruiter")
                db.add(user)
                db.commit()
            emp = db.query(Employer).filter(Employer.id == 50).first()
            if not emp:
                db.add(Employer(id=50, company_name="Tata Motors", user_id=50, trust_weight=1.0))
                db.commit()
            try:
                from sqlalchemy import text
                db.execute(text("SELECT setval(pg_get_serial_sequence('users', 'id'), (SELECT COALESCE(MAX(id), 1) FROM users));"))
                db.execute(text("SELECT setval(pg_get_serial_sequence('employers', 'id'), (SELECT COALESCE(MAX(id), 1) FROM employers));"))
                db.commit()
            except Exception:
                pass

    # =========================================================================
    # FLOW 1: STUDENT END-TO-END FLOW
    # Register -> Login -> Set Target Role -> Skill Gap Analysis -> Recommendations
    # =========================================================================
    def test_student_e2e_flow(self):
        # 1. Register student
        reg_payload = {
            "email": "priya.student@skillnexus.org",
            "password": "StrongPassword123!",
            "full_name": "Priya Sharma",
            "role": "Student"
        }
        reg_res = self.client.post("/api/v1/auth/register", json=reg_payload)
        # 201 Created or 400 if already exists
        if reg_res.status_code == 201:
            student_id = reg_res.json()["id"]
            self.assertEqual(reg_res.json()["email"], reg_payload["email"])
        else:
            self.assertEqual(reg_res.status_code, 400)
            student_id = 1

        # 2. Login
        login_res = self.client.post(
            "/api/v1/auth/login",
            json={"email": "priya.student@skillnexus.org", "password": "StrongPassword123!"}
        )
        self.assertEqual(login_res.status_code, 200)
        token = login_res.json()["access_token"]
        if reg_res.status_code != 201:
            from app.auth.jwt import verify_token
            payload = verify_token(token, expected_type="access")
            if payload and "user_id" in payload:
                student_id = payload["user_id"]

        headers = {
            "Authorization": f"Bearer {token}",
            "X-User-Role": "Student",
            "X-User-Id": str(student_id)
        }

        # 3. Set Target Role
        role_payload = {
            "user_id": student_id,
            "target_role_id": "ROLE_DATA_ENGINEER"
        }
        profile_res = self.client.post("/api/v1/students/profile", json=role_payload, headers=headers)
        self.assertEqual(profile_res.status_code, 200)
        self.assertEqual(profile_res.json()["target_role_id"], "ROLE_DATA_ENGINEER")

        # Retrieve profile
        get_profile_res = self.client.get(f"/api/v1/students/{student_id}/profile", headers=headers)
        self.assertEqual(get_profile_res.status_code, 200)

        # 4. Skill Gap Analysis
        gap_res = self.client.get("/api/v1/ml/students/STU_001/gap/ROLE_DATA_ENGINEER?mode=benchmark", headers=headers)
        self.assertEqual(gap_res.status_code, 200)
        gap_data = gap_res.json()
        self.assertIn("overall_match_score", gap_data)
        self.assertIn("skills_missing", gap_data)

        # 5. Course Candidates / Recommendations
        cand_res = self.client.get("/api/v1/ml/students/STU_001/course-candidates/ROLE_DATA_ENGINEER?mode=benchmark", headers=headers)
        self.assertEqual(cand_res.status_code, 200)
        cand_data = cand_res.json()
        self.assertIn("candidate_courses", cand_data)

    # =========================================================================
    # FLOW 2: EMPLOYER END-TO-END FLOW
    # Login -> Post Job -> Submit Feedback
    # =========================================================================
    def test_employer_e2e_flow(self):
        headers = {
            "X-User-Role": "Employer",
            "X-User-Id": "50",
            "X-User-Email": "recruiter@tata.com"
        }

        # 1. Post job
        job_payload = {
            "title": "Senior EV Systems Engineer",
            "company": "Tata Motors",
            "location": "Pune",
            "description": "Seeking expert in Battery Management Systems (BMS), CAN bus communications, and vehicle telematics."
        }
        job_res = self.client.post("/api/v1/jobs/", json=job_payload, headers=headers)
        self.assertEqual(job_res.status_code, 201)
        job_data = job_res.json()
        self.assertIn("id", job_data)
        self.assertIn("extracted_skills", job_data)

        # 2. Submit feedback (testing optional employer_id)
        feedback_payload = {
            "comments": "Graduates demonstrate solid battery fundamentals but lack experience with CAN-FD and high voltage safety.",
            "rating": 4
        }
        fb_res = self.client.post("/api/v1/employers/feedback", json=feedback_payload, headers=headers)
        self.assertEqual(fb_res.status_code, 201)
        fb_data = fb_res.json()
        self.assertIn("signals", fb_data)
        self.assertIn("employer_id", fb_data)

    # =========================================================================
    # FLOW 3: INSTITUTE END-TO-END FLOW
    # View Courses -> View Course Gaps by Course ID
    # =========================================================================
    def test_institute_e2e_flow(self):
        headers = {
            "X-User-Role": "Institute",
            "X-User-Id": "20",
            "X-User-Email": "director@vjti.ac.in"
        }

        # 1. List Courses
        courses_res = self.client.get("/api/v1/courses/", headers=headers)
        self.assertEqual(courses_res.status_code, 200)
        courses = courses_res.json()
        self.assertIsInstance(courses, list)

        # 2. View Course Gap for specific course (e.g. 1)
        gap_res = self.client.get("/api/v1/ml/course-gaps/1", headers=headers)
        self.assertEqual(gap_res.status_code, 200)
        gap_data = gap_res.json()
        self.assertEqual(gap_data["course_id"], 1)
        self.assertIn("gap_score", gap_data)
        self.assertIn("missing_skills", gap_data)
        self.assertIn("recommendations", gap_data)

    # =========================================================================
    # FLOW 4: TRAINER END-TO-END FLOW
    # View Demand -> View Evidence Summary
    # =========================================================================
    def test_trainer_e2e_flow(self):
        headers = {
            "X-User-Role": "Trainer",
            "X-User-Id": "30",
            "X-User-Email": "trainer@msde.gov.in"
        }

        # 1. View Demand (with top_n query param)
        demand_res = self.client.get("/api/v1/ml/demand?top_n=8&mode=benchmark", headers=headers)
        self.assertEqual(demand_res.status_code, 200)

        # 2. View Evidence Summary for skill
        evidence_res = self.client.get("/api/v1/ml/evidence-summary/SK_SQL", headers=headers)
        self.assertEqual(evidence_res.status_code, 200)
        ev_data = evidence_res.json()
        self.assertEqual(ev_data["skill_id"], "SK_SQL")
        self.assertIn("confidence_distribution", ev_data)
        self.assertIn("employer_signal_weight", ev_data)

    # =========================================================================
    # FLOW 5: FRONTEND API COMPATIBILITY CHECKS
    # Skill by code, Course Skills by course id, Student Profile alias
    # =========================================================================
    def test_frontend_compatibility_routes(self):
        headers = {"X-User-Role": "Admin"}

        # 1. Course skills by course id
        cs_res = self.client.get("/api/v1/course-skills/course/1", headers=headers)
        self.assertEqual(cs_res.status_code, 200)

        # 2. Student profile alias
        stu_alias_res = self.client.get("/api/v1/ml/students/STU_001?mode=benchmark", headers=headers)
        self.assertEqual(stu_alias_res.status_code, 200)
        self.assertIn("student_id", stu_alias_res.json())
