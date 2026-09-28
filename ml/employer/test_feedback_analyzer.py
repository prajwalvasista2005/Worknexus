import unittest
import json
import tempfile
from pathlib import Path
from ml.employer.feedback_analyzer import EmployerFeedbackAnalyzer, DEFAULT_FEEDBACK_PATH, DEFAULT_TAXONOMY_PATH

class TestEmployerFeedbackAnalyzer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analyzer = EmployerFeedbackAnalyzer()
        cls.artifact = cls.analyzer.analyze()

    def test_01_input_count(self):
        with open(DEFAULT_FEEDBACK_PATH, "r", encoding="utf-8") as f:
            src_data = json.load(f)
        self.assertEqual(self.artifact["metadata"]["total_feedback_records"], len(src_data))
        self.assertEqual(self.artifact["metadata"]["processed_feedback_records"], len(src_data))
        self.assertEqual(self.artifact["metadata"]["failed_feedback_records"], 0)

    def test_02_extraction_input(self):
        # Verify skills are extracted from the text
        fb1 = next(r for r in self.artifact["feedback_records"] if r["employer_id"] == 17)
        extracted_ids = {s["skill_id"] for s in fb1["skills"]}
        self.assertIn("SK_CAN", extracted_ids)

    def test_03_output_contract(self):
        for fb in self.artifact["feedback_records"]:
            for s in fb["skills"]:
                self.assertIn("skill_id", s)
                self.assertIn("confidence_score", s)
                self.assertIn("trust_weight", s)
                self.assertIn("weighted_signal", s)

    def test_04_taxonomy(self):
        with open(DEFAULT_TAXONOMY_PATH, "r", encoding="utf-8") as f:
            tax = json.load(f)
        valid_ids = {s["id"] for s in tax}
        for s in self.artifact["skill_signals"]:
            self.assertIn(s["skill_id"], valid_ids)

    def test_05_trust_weight(self):
        fb1 = next(r for r in self.artifact["feedback_records"] if r["employer_id"] == 17)
        for s in fb1["skills"]:
            expected_weighted = s["confidence_score"] * s["trust_weight"]
            self.assertAlmostEqual(s["weighted_signal"], expected_weighted, places=5)

    def test_06_no_trust_fabrication(self):
        # Test missing trust weight in raw record
        test_data = [{"employer_id": 999, "comment": "Great Python developer", "course_id": 101}]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(test_data, f)
            temp_path = Path(f.name)
        try:
            res = EmployerFeedbackAnalyzer(feedback_path=temp_path).analyze()
            rec = res["feedback_records"][0]
            self.assertEqual(rec["trust_weight"], 1.0)
            py_skill = rec["skills"][0]
            self.assertEqual(py_skill["weighted_signal"], py_skill["confidence_score"])
        finally:
            temp_path.unlink(missing_ok=True)

    def test_07_duplicate_skill_within_feedback(self):
        test_data = [{
            "employer_id": 888,
            "trust_weight": 0.8,
            "comment": "Python is great. We love Python programming and Python scripts.",
            "course_id": 101
        }]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(test_data, f)
            temp_path = Path(f.name)
        try:
            res = EmployerFeedbackAnalyzer(feedback_path=temp_path).analyze()
            py_signals = [s for s in res["feedback_records"][0]["skills"] if s["skill_id"] == "SK_PYTHON"]
            self.assertEqual(len(py_signals), 1)
            sig = res["skill_signals"][0]
            self.assertEqual(sig["feedback_count"], 1)
            self.assertEqual(sig["unique_employer_count"], 1)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_08_unique_employer_count(self):
        # 2 feedbacks from employer 777
        test_data = [
            {"employer_id": 777, "trust_weight": 0.9, "comment": "Good Python engineer", "course_id": 101},
            {"employer_id": 777, "trust_weight": 0.9, "comment": "Another strong Python hire", "course_id": 101}
        ]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(test_data, f)
            temp_path = Path(f.name)
        try:
            res = EmployerFeedbackAnalyzer(feedback_path=temp_path).analyze()
            sig = res["skill_signals"][0]
            self.assertEqual(sig["feedback_count"], 2)
            self.assertEqual(sig["unique_employer_count"], 1)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_09_feedback_count(self):
        can_sig = next(s for s in self.artifact["skill_signals"] if s["skill_id"] == "SK_CAN")
        self.assertEqual(can_sig["feedback_count"], 3)
        self.assertEqual(can_sig["unique_employer_count"], 3)

    def test_10_aggregation(self):
        can_sig = next(s for s in self.artifact["skill_signals"] if s["skill_id"] == "SK_CAN")
        # Employer 17 (0.9 * 0.99 = 0.891) + Employer 22 (1.0 * 0.96 = 0.96) + Employer 31 (0.7 * 0.96 = 0.672)
        expected_sum = (0.9 * 0.99) + (1.0 * 0.96) + (0.7 * 0.96)
        self.assertAlmostEqual(can_sig["weighted_signal_sum"], round(expected_sum, 6), places=4)
        expected_avg = expected_sum / 3.0
        self.assertAlmostEqual(can_sig["average_weighted_signal"], round(expected_avg, 6), places=4)

    def test_11_zero_skill_feedback(self):
        test_data = [{"employer_id": 555, "trust_weight": 0.8, "comment": "Great communication and punctuality.", "course_id": 42}]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(test_data, f)
            temp_path = Path(f.name)
        try:
            res = EmployerFeedbackAnalyzer(feedback_path=temp_path).analyze()
            self.assertEqual(res["metadata"]["zero_skill_feedback_records"], 1)
            self.assertEqual(len(res["feedback_records"]), 1)
            self.assertEqual(res["feedback_records"][0]["skills"], [])
        finally:
            temp_path.unlink(missing_ok=True)

    def test_12_course_association(self):
        c42 = next(c for c in self.artifact["course_signals"] if c["course_id"] == 42)
        self.assertEqual(c42["feedback_count"], 4)
        self.assertEqual(c42["employer_count"], 4)
        self.assertIn("SK_CAN", c42["skills_mentioned"])
        self.assertIn("SK_BMS", c42["skills_mentioned"])

    def test_13_determinism(self):
        run2 = EmployerFeedbackAnalyzer().analyze()
        self.assertEqual(json.dumps(self.artifact, sort_keys=True), json.dumps(run2, sort_keys=True))

    def test_14_error_visibility(self):
        test_data = [{"employer_id": 123, "trust_weight": "INVALID_NUMBER", "comment": "Python"}]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(test_data, f)
            temp_path = Path(f.name)
        try:
            res = EmployerFeedbackAnalyzer(feedback_path=temp_path).analyze()
            self.assertEqual(res["metadata"]["failed_feedback_records"], 1)
            self.assertEqual(len(res["errors"]), 1)
            self.assertIn("Invalid trust_weight", res["errors"][0]["error"])
        finally:
            temp_path.unlink(missing_ok=True)

    def test_15_no_demand_dependency(self):
        # Verify analyzer initializes and runs without demand_analysis.json
        analyzer = EmployerFeedbackAnalyzer()
        res = analyzer.analyze()
        self.assertNotIn("demand_input", res["metadata"])

    def test_16_no_recommendation_logic(self):
        raw_json = json.dumps(self.artifact).lower()
        forbidden = ["recommend", "should add", "suggest", "actionable", "must teach"]
        for fb in forbidden:
            self.assertNotIn(fb, raw_json)

if __name__ == "__main__":
    unittest.main()
