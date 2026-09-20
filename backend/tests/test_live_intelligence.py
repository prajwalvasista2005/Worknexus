import unittest
from backend.app.db.session import MockDatabaseSession
from backend.app.models.entities import JobPosting, JobSkill, Course, CourseSkill, Employer, EmployerFeedback, EmployerFeedbackSignal
from backend.app.services.ml_adapter import MLAdapter, get_ml_adapter, HTTPException

class TestLiveIntelligenceIntegration(unittest.TestCase):

    def setUp(self):
        self.db = MockDatabaseSession()
        self.adapter = MLAdapter()

        # 1. Seed Employers
        self.emp1 = Employer(id=1, company_name="Tata Motors EV", trust_weight=1.0)
        self.emp2 = Employer(id=2, company_name="Ola Electric", trust_weight=0.8)
        self.db.add(self.emp1)
        self.db.add(self.emp2)

        # 2. Seed Job Postings (3 with skills, 1 zero-skill job -> total 4)
        j1 = JobPosting(id=1, title="EV Battery Engineer", company="Tata Motors", location="Pune", description="BMS and Python")
        j2 = JobPosting(id=2, title="Data Engineer", company="Ola", location="Bengaluru", description="Python and SQL")
        j3 = JobPosting(id=3, title="Backend Developer", company="Nexus", location="Mumbai", description="FastAPI and Docker")
        j4 = JobPosting(id=4, title="Operations Associate", company="Nexus", location="Remote", description="General management") # Zero-skill job
        self.db.add(j1)
        self.db.add(j2)
        self.db.add(j3)
        self.db.add(j4)

        # Skills for j1: SK_BMS, SK_PYTHON
        self.db.add(JobSkill(id=1, job_id=1, skill_id="SK_BMS", confidence_score=0.99))
        self.db.add(JobSkill(id=2, job_id=1, skill_id="SK_PYTHON", confidence_score=0.99))

        # Skills for j2: SK_PYTHON, SK_SQL
        self.db.add(JobSkill(id=3, job_id=2, skill_id="SK_PYTHON", confidence_score=0.99))
        self.db.add(JobSkill(id=4, job_id=2, skill_id="SK_SQL", confidence_score=0.99))

        # Skills for j3: SK_FASTAPI, SK_DOCKER
        self.db.add(JobSkill(id=5, job_id=3, skill_id="SK_FASTAPI", confidence_score=0.96))
        self.db.add(JobSkill(id=6, job_id=3, skill_id="SK_DOCKER", confidence_score=0.96))

        # 3. Seed Courses
        # Course 101: Teaches SK_PYTHON, SK_SQL
        c1 = Course(id=101, name="Data Engineering Fundamentals")
        self.db.add(c1)
        self.db.add(CourseSkill(course_id=101, skill_id="SK_PYTHON", coverage_pct=100.0))
        self.db.add(CourseSkill(course_id=101, skill_id="SK_SQL", coverage_pct=100.0))

        # Course 102: Teaches SK_CAN (Course skill without observed job demand)
        c2 = Course(id=102, name="Automotive Protocols")
        self.db.add(c2)
        self.db.add(CourseSkill(course_id=102, skill_id="SK_CAN", coverage_pct=100.0))

        # 4. Seed Employer Feedback
        fb1 = EmployerFeedback(id=1, employer_id=1, comments="Strong BMS knowledge", rating=5)
        fb2 = EmployerFeedback(id=2, employer_id=2, comments="Needs CAN bus and Battery cell skills", rating=4)
        self.db.add(fb1)
        self.db.add(fb2)

        # Signal for fb1 (Employer 1, trust 1.0): SK_BMS
        self.db.add(EmployerFeedbackSignal(id=1, feedback_id=1, skill_id="SK_BMS", confidence_score=0.99, trust_weight=1.0, weighted_signal=0.99))

        # Signals for fb2 (Employer 2, trust 0.8): SK_CAN, SK_BATTERY_CELL
        self.db.add(EmployerFeedbackSignal(id=2, feedback_id=2, skill_id="SK_CAN", confidence_score=0.96, trust_weight=0.8, weighted_signal=0.768))
        self.db.add(EmployerFeedbackSignal(id=3, feedback_id=2, skill_id="SK_BATTERY_CELL", confidence_score=0.96, trust_weight=0.8, weighted_signal=0.768))

    def test_01_live_demand_computation(self):
        """Test live demand aggregation from database records."""
        demand = self.adapter.get_skill_demand(db=self.db, mode="live")
        self.assertFalse(demand.is_synthetic_artifact)
        self.assertEqual(demand.total_jobs_analyzed, 4) # Denominator includes zero-skill job
        self.assertEqual(demand.total_unique_skills_demanded, 5) # SK_BMS, SK_PYTHON, SK_SQL, SK_FASTAPI, SK_DOCKER

        # SK_PYTHON appears in 2 jobs -> demand_share = 2/4 = 0.5
        py_skill = next((s for s in demand.top_skills if s["skill_id"] == "SK_PYTHON"), None)
        self.assertIsNotNone(py_skill)
        self.assertEqual(py_skill["job_count"], 2)
        self.assertEqual(py_skill["demand_share"], 0.5)

    def test_02_benchmark_demand_computation(self):
        """Test benchmark demand retrieval loads Phase 3 synthetic artifact."""
        demand = self.adapter.get_skill_demand(db=self.db, mode="benchmark")
        self.assertTrue(demand.is_synthetic_artifact)
        self.assertEqual(demand.total_jobs_analyzed, 295)

    def test_03_live_course_gaps_computation(self):
        """Test live course gap analysis against live demand."""
        gaps = self.adapter.get_course_skill_gaps(db=self.db, mode="live")
        self.assertFalse(gaps.is_synthetic_artifact)
        self.assertEqual(gaps.total_courses_analyzed, 2)
        self.assertEqual(gaps.total_skills_demanded, 5)

        c101 = next((c for c in gaps.course_gaps if c["course_id"] == 101), None)
        self.assertIsNotNone(c101)
        self.assertEqual(c101["covered_skills"], ["SK_PYTHON", "SK_SQL"])
        # missing: SK_BMS, SK_DOCKER, SK_FASTAPI
        self.assertEqual(c101["missing_skills"], ["SK_BMS", "SK_DOCKER", "SK_FASTAPI"])

        c102 = next((c for c in gaps.course_gaps if c["course_id"] == 102), None)
        self.assertIsNotNone(c102)
        self.assertEqual(c102["course_skills_without_observed_demand"], ["SK_CAN"])

    def test_04_live_multi_signal_evidence(self):
        """Test live multi-signal evidence uniting live demand and employer signals."""
        evidence = self.adapter.get_skill_evidence(db=self.db, mode="live")
        self.assertFalse(evidence.is_synthetic_artifact)
        
        skills_map = {s["skill_id"]: s for s in evidence.multi_signal_skills}
        
        # SK_BMS in both job demand and employer feedback
        self.assertEqual(skills_map["SK_BMS"]["evidence_relationship"], "both")
        
        # SK_PYTHON only in job demand
        self.assertEqual(skills_map["SK_PYTHON"]["evidence_relationship"], "job_only")
        
        # SK_CAN only in employer feedback
        self.assertEqual(skills_map["SK_CAN"]["evidence_relationship"], "employer_feedback_only")
        self.assertAlmostEqual(skills_map["SK_CAN"]["employer_validation"]["weighted_signal_sum"], 0.768, places=3)

    def test_05_live_generic_recommendations(self):
        """Test live generic skill recommendations evaluated with Phase 6A rules."""
        recs = self.adapter.get_skill_recommendations(db=self.db, mode="live")
        self.assertFalse(recs.is_synthetic_artifact)
        
        rec_ids = {s["skill_id"] for s in recs.recommended_skills}
        not_rec_ids = {s["skill_id"] for s in recs.not_recommended_skills}

        # SK_BMS: in both sources -> recommended (Condition 1)
        self.assertIn("SK_BMS", rec_ids)

        # SK_DOCKER: demanded & not covered in curriculum -> recommended (Condition 2)
        self.assertIn("SK_DOCKER", rec_ids)

        # SK_CAN: employer validated & no job demand -> recommended (Condition 3)
        self.assertIn("SK_CAN", rec_ids)

        # SK_PYTHON: demanded & covered in Course 101 & no employer validation -> not recommended
        self.assertIn("SK_PYTHON", not_rec_ids)

    def test_06_unseeded_live_student_operations(self):
        """Test that operations in live mode raise 404 when student/role entities do not exist in db."""
        with self.assertRaises(HTTPException) as ctx:
            self.adapter.get_student_skill_profile("STU_001", db=self.db, mode="live")
        self.assertEqual(ctx.exception.status_code, 404)

        with self.assertRaises(HTTPException) as ctx:
            self.adapter.get_role_skill_context("ROLE_FULL_STACK_DEV", db=self.db, mode="live")
        self.assertEqual(ctx.exception.status_code, 404)

        with self.assertRaises(HTTPException) as ctx:
            self.adapter.get_personalized_recommendations("STU_001", "ROLE_FULL_STACK_DEV", db=self.db, mode="live")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_07_benchmark_student_operations_intact(self):
        """Test that benchmark mode continues to serve Phase 7 artifacts cleanly."""
        prof = self.adapter.get_student_skill_profile("STU_001", mode="benchmark")
        self.assertTrue(prof.is_synthetic_artifact)
        self.assertEqual(prof.student_id, "STU_001")

        rec = self.adapter.get_personalized_recommendations("STU_001", "ROLE_DATA_ENGINEER", mode="benchmark")
        self.assertTrue(rec.is_synthetic_artifact)
        self.assertEqual(rec.student_id, "STU_001")

if __name__ == "__main__":
    unittest.main()
