import sys
import os
import unittest

sys.path.extend([".", "backend"])

from fastapi.testclient import TestClient
from app.main import app

class FullSystemIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

        # Test accounts seeded in database
        cls.accounts = {
            "Student": {"email": "student@worknexus.io", "password": "SecurePassword123!"},
            "Employer": {"email": "employer@worknexus.io", "password": "SecurePassword123!"},
            "Institute": {"email": "institute@worknexus.io", "password": "SecurePassword123!"},
            "Trainer": {"email": "trainer@worknexus.io", "password": "SecurePassword123!"},
            "Admin": {"email": "admin@worknexus.io", "password": "SecurePassword123!"},
        }
        cls.tokens = {}
        for role, creds in cls.accounts.items():
            res = cls.client.post("/api/v1/auth/login", json=creds)
            assert res.status_code == 200, f"Login failed for {role}: {res.text}"
            cls.tokens[role] = res.json()["access_token"]

    def _header(self, role: str):
        return {"Authorization": f"Bearer {self.tokens[role]}"}

    # 1. Root & Health
    def test_01_health_and_root(self):
        r1 = self.client.get("/")
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()["status"], "healthy")

        r2 = self.client.get("/health")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["status"], "healthy")

    # 2. Auth Flow
    def test_02_auth_me_and_refresh(self):
        # /me
        for role in self.accounts.keys():
            res = self.client.get("/api/v1/auth/me", headers=self._header(role))
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["email"], self.accounts[role]["email"])

        # Token refresh
        res_login = self.client.post("/api/v1/auth/login", json=self.accounts["Student"])
        refresh_token = res_login.json()["refresh_token"]
        res_ref = self.client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        self.assertEqual(res_ref.status_code, 200)
        self.assertIn("access_token", res_ref.json())

    # 3. Student Workflow
    def test_03_student_workflow(self):
        headers = self._header("Student")
        me = self.client.get("/api/v1/auth/me", headers=headers).json()
        student_id = me["id"]

        # List Roles
        roles_res = self.client.get("/api/v1/roles/", headers=headers)
        self.assertEqual(roles_res.status_code, 200)
        roles = roles_res.json()
        self.assertGreater(len(roles), 0)
        target_role = roles[0]["id"]

        # Save Target Role Profile
        prof_res = self.client.post("/api/v1/students/profile", json={
            "user_id": student_id,
            "target_role_id": target_role
        }, headers=headers)
        self.assertEqual(prof_res.status_code, 200)

        # Get Profile
        p_res = self.client.get(f"/api/v1/students/{student_id}/profile", headers=headers)
        self.assertEqual(p_res.status_code, 200)

        # ML Student Gap
        gap_res = self.client.get(f"/api/v1/ml/students/{student_id}/gap/{target_role}", headers=headers)
        self.assertEqual(gap_res.status_code, 200)
        gap_data = gap_res.json()
        self.assertIn("overall_match_score", gap_data)
        self.assertIn("acquired_skills", gap_data)
        self.assertIn("missing_skills", gap_data)

        # ML Course Candidates
        cc_res = self.client.get(f"/api/v1/ml/students/{student_id}/course-candidates/{target_role}", headers=headers)
        self.assertEqual(cc_res.status_code, 200)
        self.assertIn("candidate_courses", cc_res.json())

        # Submit Evidence
        ev_res = self.client.post(f"/api/v1/students/{student_id}/evidence", json={
            "skill_id": "SKILL_PYTHON",
            "evidence_type": "project",
            "strength": "advanced",
            "metadata": {"repo": "https://github.com/demo/repo", "commits": 12}
        }, headers=headers)
        self.assertEqual(ev_res.status_code, 201)

        # List Evidence
        ev_list = self.client.get(f"/api/v1/students/{student_id}/evidence", headers=headers)
        self.assertEqual(ev_list.status_code, 200)
        self.assertGreater(len(ev_list.json()), 0)

        # Direct User Skills CRUD
        my_skills = self.client.get("/api/v1/user-skills/me", headers=headers)
        self.assertEqual(my_skills.status_code, 200)

        add_skill = self.client.post("/api/v1/user-skills/", json={
            "skill_id": 1,
            "proficiency_level": "intermediate",
            "source": "self_reported"
        }, headers=headers)
        if add_skill.status_code == 201:
            skill_entry_id = add_skill.json()["id"]
            # Delete user skill
            del_sk = self.client.delete(f"/api/v1/user-skills/{skill_entry_id}", headers=headers)
            self.assertEqual(del_sk.status_code, 200)

        # Tailored Recommendations
        rec_res = self.client.get(f"/api/v1/ml/students/{student_id}/recommendations/{target_role}", headers=headers)
        self.assertEqual(rec_res.status_code, 200)

    # 4. Employer Workflow
    def test_04_employer_workflow(self):
        headers = self._header("Employer")

        # Submit Job Demand Requisition with Automatic ML extraction
        job_res = self.client.post("/api/v1/jobs/", json={
            "company_name": "Nexus Dynamics Inc",
            "contact_information": "hiring@nexusdynamics.io",
            "industry": "Artificial Intelligence",
            "job_title": "Full Stack ML Systems Engineer",
            "location": "Bengaluru, India / Remote",
            "required_skills": ["Python", "FastAPI", "Docker", "PyTorch"],
            "missing_candidate_skills": ["Kubernetes"],
            "comments": "Looking for production microservices experience with FastAPI and container deployment."
        }, headers=headers)
        self.assertEqual(job_res.status_code, 201)
        job_data = job_res.json()
        self.assertIn("id", job_data)
        self.assertIn("extracted_skills", job_data)
        created_job_id = job_data["id"]

        # List Jobs
        jobs_list = self.client.get("/api/v1/jobs/", headers=headers)
        self.assertEqual(jobs_list.status_code, 200)
        self.assertGreater(len(jobs_list.json()), 0)

        # Get Single Job
        single_job = self.client.get(f"/api/v1/jobs/{created_job_id}", headers=headers)
        self.assertEqual(single_job.status_code, 200)

        # Submit Employer Feedback with ML Signals
        fb_res = self.client.post("/api/v1/employers/feedback", json={
            "job_title": "Full Stack ML Systems Engineer",
            "comments": "Graduates show exceptional Python knowledge but require more hands-on Docker and Kubernetes experience.",
            "feedback_text": "Graduates show exceptional Python knowledge but require more hands-on Docker and Kubernetes experience.",
            "rating": 4
        }, headers=headers)
        self.assertEqual(fb_res.status_code, 201)
        fb_data = fb_res.json()
        self.assertIn("id", fb_data)

        # List Feedbacks
        fb_list = self.client.get("/api/v1/employers/feedback", headers=headers)
        self.assertEqual(fb_list.status_code, 200)
        self.assertGreater(len(fb_list.json()), 0)

        # Delete Job
        del_job = self.client.delete(f"/api/v1/jobs/{created_job_id}", headers=headers)
        self.assertEqual(del_job.status_code, 200)

    # 5. Institute Workflow
    def test_05_institute_workflow(self):
        headers = self._header("Institute")

        # List Courses
        courses = self.client.get("/api/v1/courses/", headers=headers)
        self.assertEqual(courses.status_code, 200)
        all_c = courses.json()
        self.assertGreater(len(all_c), 0)
        test_course_id = all_c[0]["id"]

        # Create Course
        new_c_code = "CS-AUTO-TEST-101"
        create_c = self.client.post("/api/v1/courses/", json={
            "course_id": new_c_code,
            "name": "Cloud Native Distributed Systems",
            "department": "Computer Science",
            "description": "Comprehensive course on distributed architectures, cloud native design, and microservices.",
            "is_active": True
        }, headers=headers)
        self.assertIn(create_c.status_code, [201, 400])
        created_c_id = create_c.json()["id"] if create_c.status_code == 201 else None

        # Course Gap Analysis
        gap_res = self.client.get(f"/api/v1/ml/course-gaps/{test_course_id}", headers=headers)
        self.assertEqual(gap_res.status_code, 200)
        gap_data = gap_res.json()
        self.assertIn("gap_score", gap_data)
        self.assertIn("coverage_pct", gap_data)

        # Course Skills
        c_skills = self.client.get(f"/api/v1/courses/{test_course_id}/skills", headers=headers)
        self.assertEqual(c_skills.status_code, 200)

        # Add Direct Skill to Course
        link_res = self.client.post(f"/api/v1/courses/{test_course_id}/skills", json={
            "skill_id": 1,
            "relevance_score": 1.0
        }, headers=headers)
        self.assertIn(link_res.status_code, [200, 201])

        # Delete Course if created
        if created_c_id:
            del_c = self.client.delete(f"/api/v1/courses/{created_c_id}", headers=headers)
            self.assertEqual(del_c.status_code, 200)

    # 6. Trainer Hub Workflow
    def test_06_trainer_hub_workflow(self):
        headers = self._header("Trainer")

        # Demand Rankings
        demand = self.client.get("/api/v1/ml/demand?top_n=10", headers=headers)
        self.assertEqual(demand.status_code, 200)
        skills = demand.json().get("demands", demand.json().get("top_skills", []))
        self.assertGreater(len(skills), 0)
        test_skill_id = skills[0]["skill_id"]

        # Evidence Summary for Skill
        summary = self.client.get(f"/api/v1/ml/evidence-summary/{test_skill_id}", headers=headers)
        self.assertEqual(summary.status_code, 200)
        self.assertIn("confidence_distribution", summary.json())

        # AI Skill Extractor
        extract = self.client.post("/api/v1/ml/extract-skills", json={
            "text": "Requires strong proficiency in Python, FastAPI, Docker, and Kubernetes with SQL databases."
        }, headers=headers)
        self.assertEqual(extract.status_code, 200)
        extracted = extract.json().get("skills", [])
        self.assertGreater(len(extracted), 0)

        # Generic Recommendations
        recs = self.client.get("/api/v1/ml/recommendations?mode=live", headers=headers)
        self.assertEqual(recs.status_code, 200)

        # Multi-Signal Evidence
        evidence = self.client.get("/api/v1/ml/evidence?mode=live", headers=headers)
        self.assertEqual(evidence.status_code, 200)

    # 7. Admin Workflow
    def test_07_admin_workflow(self):
        headers = self._header("Admin")

        # Create Target Role
        role_id = "ROLE_AUTOMATION_LEAD"
        role_res = self.client.post("/api/v1/roles/", json={
            "id": role_id,
            "name": "Automation & Integration Lead",
            "description": "Architects automated end-to-end integration and workforce testing suites.",
            "skill_ids": ["SKILL_PYTHON", "SKILL_FASTAPI", "SKILL_DOCKER"]
        }, headers=headers)
        self.assertIn(role_res.status_code, [201, 422])

        # Get Skills Catalog
        skills_res = self.client.get("/api/v1/skills/", headers=headers)
        self.assertEqual(skills_res.status_code, 200)
        self.assertGreater(len(skills_res.json()), 0)

        # Create Skill
        new_sk_code = "SKILL_VUEJS_3"
        sk_create = self.client.post("/api/v1/skills/", json={
            "skill_id": new_sk_code,
            "name": "Vue.js 3 Framework",
            "category": "Frontend",
            "description": "Progressive JavaScript framework for user interfaces."
        }, headers=headers)
        self.assertIn(sk_create.status_code, [201, 400])
        if sk_create.status_code == 201:
            created_id = sk_create.json()["id"]
            # Delete Skill
            del_sk = self.client.delete(f"/api/v1/skills/{created_id}", headers=headers)
            self.assertEqual(del_sk.status_code, 200)

if __name__ == "__main__":
    unittest.main()
