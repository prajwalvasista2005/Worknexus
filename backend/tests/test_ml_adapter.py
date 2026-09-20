import unittest
from backend.app.services.ml_adapter import MLAdapter, get_ml_adapter, HTTPException

class TestMLAdapter(unittest.TestCase):

    def setUp(self):
        self.adapter = get_ml_adapter()

    def test_01_extract_skills_success(self):
        """Test skill extraction through MLAdapter."""
        text = "Seeking EV engineer with BMS, CAN Bus, and Battery Testing experience."
        skills = self.adapter.extract_skills(text)
        self.assertIsInstance(skills, list)
        self.assertGreaterEqual(len(skills), 2)
        skill_ids = {s["skill_id"] for s in skills}
        self.assertIn("SK_BMS", skill_ids)
        self.assertIn("SK_CAN", skill_ids)
        for s in skills:
            self.assertIn("confidence_score", s)
            self.assertIsInstance(s["confidence_score"], float)

    def test_02_extract_skills_invalid_input(self):
        """Test skill extraction handles empty/invalid input with 422 HTTPException."""
        with self.assertRaises(HTTPException) as ctx:
            self.adapter.extract_skills("")
        self.assertEqual(ctx.exception.status_code, 422)

    def test_03_process_job_success(self):
        """Test job processing through MLAdapter."""
        job_data = {
            "id": "JOB_TEST_100",
            "title": "Full Stack Developer",
            "company": "Tech Solutions",
            "location": "Mumbai",
            "description": "Must have hands-on experience in Python, FastAPI, and Docker."
        }
        res = self.adapter.process_job(job_data)
        self.assertEqual(res.job_id, "JOB_TEST_100")
        self.assertEqual(res.title, "Full Stack Developer")
        extracted_ids = {s["skill_id"] for s in res.extracted_skills}
        self.assertIn("SK_PYTHON", extracted_ids)
        self.assertIn("SK_FASTAPI", extracted_ids)
        self.assertIn("SK_DOCKER", extracted_ids)

    def test_04_analyze_employer_feedback_success(self):
        """Test employer feedback intelligence through MLAdapter."""
        fb_data = {
            "feedback_id": "FB_TEST_100",
            "employer_id": 42,
            "course_id": 101,
            "trust_weight": 0.8,
            "comments": "The candidate has excellent Docker and SQL skills."
        }
        res = self.adapter.analyze_employer_feedback(fb_data)
        self.assertEqual(res.total_feedback_records, 1)
        detected_ids = {s["skill_id"] for s in res.detected_skills}
        self.assertIn("SK_DOCKER", detected_ids)
        self.assertIn("SK_SQL", detected_ids)

        for sig in res.detected_skills:
            if sig["skill_id"] == "SK_DOCKER":
                # confidence * trust_weight (0.96 * 0.8 = 0.768)
                self.assertAlmostEqual(sig["weighted_signal_sum"], 0.96 * 0.8, places=3)

if __name__ == "__main__":
    unittest.main()
