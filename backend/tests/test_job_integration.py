import unittest
from backend.app.db.session import MockDatabaseSession
from backend.app.models.entities import JobPosting, JobSkill
from backend.app.schemas.schemas import JobCreateSchema
from backend.app.services.job_service import JobService
from backend.app.services.ml_adapter import MLAdapter

class TestJobIntegration(unittest.TestCase):

    def setUp(self):
        self.db = MockDatabaseSession()
        self.adapter = MLAdapter()

    def test_job_creation_with_extracted_skills(self):
        """Test full job posting flow with ML extraction and persistence."""
        job_in = JobCreateSchema(
            title="Data Platform Engineer",
            company="Cloud Nexus",
            location="Pune",
            description="Looking for an engineer skilled in Apache Airflow, Python, and SQL queries.",
            employer_id=1
        )

        res = JobService.create_job(db=self.db, job_in=job_in, ml_adapter=self.adapter)

        # 1. Verify response structure
        self.assertIsNotNone(res.id)
        self.assertEqual(res.title, "Data Platform Engineer")
        extracted_ids = {s.skill_id for s in res.extracted_skills}
        self.assertIn("SK_AIRFLOW", extracted_ids)
        self.assertIn("SK_PYTHON", extracted_ids)
        self.assertIn("SK_SQL", extracted_ids)

        # 2. Verify database persistence
        db_job = self.db.query(JobPosting).filter(lambda j: j.id == res.id).first()
        self.assertIsNotNone(db_job)
        self.assertEqual(db_job.title, "Data Platform Engineer")

        # 3. Verify JobSkill rows
        db_skills = self.db.query(JobSkill).filter(lambda s: s.job_id == res.id).all()
        self.assertEqual(len(db_skills), len(extracted_ids))
        db_skill_ids = {s.skill_id for s in db_skills}
        self.assertEqual(db_skill_ids, extracted_ids)

        for s in db_skills:
            self.assertGreaterEqual(s.confidence_score, 0.9)

if __name__ == "__main__":
    unittest.main()
