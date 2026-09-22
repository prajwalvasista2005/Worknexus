import unittest
from app.db.session import MockDatabaseSession
from app.models.entities import Employer, EmployerFeedback, EmployerFeedbackSignal
from app.schemas.schemas import EmployerFeedbackCreateSchema
from app.services.employer_service import EmployerService
from app.services.ml_adapter import MLAdapter

class TestEmployerFeedbackIntegration(unittest.TestCase):

    def setUp(self):
        self.db = MockDatabaseSession()
        self.adapter = MLAdapter()

        # Seed test employer with trust_weight = 0.9
        self.employer = Employer(id=17, company_name="Tata Motors EV", trust_weight=0.9)
        self.db.add(self.employer)

    def test_employer_feedback_submission_with_weighted_signals(self):
        """Test employer feedback flow with trust weighting and signal persistence."""
        fb_in = EmployerFeedbackCreateSchema(
            employer_id=17,
            course_id=42,
            comments="Trainees demonstrate solid Vehicle Diagnostics and Thermal Management competencies.",
            rating=5
        )

        res = EmployerService.submit_feedback(db=self.db, feedback_in=fb_in, ml_adapter=self.adapter)

        # 1. Verify response structure
        self.assertIsNotNone(res.id)
        self.assertEqual(res.employer_id, 17)
        self.assertEqual(res.course_id, 42)
        signal_ids = {s.skill_id for s in res.signals}
        self.assertIn("SK_DIAG", signal_ids)
        self.assertIn("SK_THERMAL", signal_ids)

        # 2. Verify trust weighting formula: weighted_signal = confidence * trust_weight
        for sig in res.signals:
            self.assertEqual(sig.trust_weight, 0.9)
            expected_weighted = round(sig.confidence_score * 0.9, 4)
            self.assertAlmostEqual(sig.weighted_signal, expected_weighted, places=3)

        # 3. Verify database persistence
        db_fb = self.db.query(EmployerFeedback).filter(lambda f: f.id == res.id).first()
        self.assertIsNotNone(db_fb)
        self.assertEqual(db_fb.comments, fb_in.comments)

        db_signals = self.db.query(EmployerFeedbackSignal).filter(lambda s: s.feedback_id == res.id).all()
        self.assertEqual(len(db_signals), len(signal_ids))

if __name__ == "__main__":
    unittest.main()
