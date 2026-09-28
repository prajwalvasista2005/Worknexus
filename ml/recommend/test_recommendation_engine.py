import unittest
import json
from pathlib import Path
from ml.recommend.recommendation_engine import (
    GenericSkillRecommendationEngine,
    DEFAULT_EVIDENCE_PATH,
    DEFAULT_GAP_PATH,
    DEFAULT_TAXONOMY_PATH
)

class TestGenericSkillRecommendationEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = GenericSkillRecommendationEngine()
        cls.artifact = cls.engine.recommend()

    def test_01_evidence_input(self):
        with open(DEFAULT_EVIDENCE_PATH, "r", encoding="utf-8") as f:
            ev_data = json.load(f)
        self.assertEqual(self.artifact["metadata"]["total_skills"], len(ev_data["skills"]))

    def test_02_course_gap_input(self):
        with open(DEFAULT_GAP_PATH, "r", encoding="utf-8") as f:
            gap_data = json.load(f)
        self.assertGreater(len(gap_data["courses"]), 0)

    def test_03_taxonomy_validation(self):
        with open(DEFAULT_TAXONOMY_PATH, "r", encoding="utf-8") as f:
            tax = json.load(f)
        valid_ids = {s["id"] for s in tax}
        for rec in self.artifact["recommendations"]:
            self.assertIn(rec["skill_id"], valid_ids)

    def test_04_skill_universe(self):
        with open(DEFAULT_EVIDENCE_PATH, "r", encoding="utf-8") as f:
            ev_data = json.load(f)
        ev_ids = {s["skill_id"] for s in ev_data["skills"]}
        rec_ids = {s["skill_id"] for s in self.artifact["recommendations"]}
        self.assertEqual(ev_ids, rec_ids)
        self.assertEqual(len(rec_ids), 35)

    def test_05_market_demand_rule(self):
        for rec in self.artifact["recommendations"]:
            j_dem = rec["evidence"]["job_demand"]
            expected = bool(j_dem.get("observed") and (j_dem.get("job_count") or 0) > 0)
            self.assertEqual(rec["decision_factors"]["market_demand"], expected)

    def test_06_employer_rule(self):
        for rec in self.artifact["recommendations"]:
            e_val = rec["evidence"]["employer_validation"]
            expected = bool(e_val.get("observed") and (e_val.get("unique_employer_count") or 0) > 0)
            self.assertEqual(rec["decision_factors"]["employer_validation"], expected)

    def test_07_course_coverage(self):
        py_rec = next(r for r in self.artifact["recommendations"] if r["skill_id"] == "SK_PYTHON")
        self.assertTrue(py_rec["decision_factors"]["course_coverage"])
        self.assertEqual(py_rec["course_context"]["covering_course_ids"], [101, 102])

        aws_rec = next(r for r in self.artifact["recommendations"] if r["skill_id"] == "SK_AWS")
        self.assertFalse(aws_rec["decision_factors"]["course_coverage"])
        self.assertEqual(aws_rec["course_context"]["covering_course_ids"], [])

    def test_08_both_source_rule(self):
        py_rec = next(r for r in self.artifact["recommendations"] if r["skill_id"] == "SK_PYTHON")
        self.assertTrue(py_rec["decision_factors"]["multi_source_evidence"])

        aws_rec = next(r for r in self.artifact["recommendations"] if r["skill_id"] == "SK_AWS")
        self.assertFalse(aws_rec["decision_factors"]["multi_source_evidence"])

    def test_09_condition_1(self):
        # Python has market_demand=True and employer_validation=True -> recommended
        py_rec = next(r for r in self.artifact["recommendations"] if r["skill_id"] == "SK_PYTHON")
        self.assertEqual(py_rec["recommendation"]["status"], "recommended")
        self.assertIn("observed_market_demand", py_rec["recommendation"]["reason_ids"])
        self.assertIn("employer_validated", py_rec["recommendation"]["reason_ids"])
        self.assertIn("observed_in_both_sources", py_rec["recommendation"]["reason_ids"])

    def test_10_condition_2(self):
        # AWS has market_demand=True and course_coverage=False -> recommended
        aws_rec = next(r for r in self.artifact["recommendations"] if r["skill_id"] == "SK_AWS")
        self.assertEqual(aws_rec["recommendation"]["status"], "recommended")
        self.assertIn("observed_market_demand", aws_rec["recommendation"]["reason_ids"])
        self.assertIn("course_coverage_gap", aws_rec["recommendation"]["reason_ids"])

    def test_11_condition_3(self):
        # CAN has employer_validation=True and market_demand=False -> recommended
        can_rec = next(r for r in self.artifact["recommendations"] if r["skill_id"] == "SK_CAN")
        self.assertEqual(can_rec["recommendation"]["status"], "recommended")
        self.assertIn("employer_validated", can_rec["recommendation"]["reason_ids"])
        self.assertIn("employer_only_signal", can_rec["recommendation"]["reason_ids"])

    def test_12_reason_ids(self):
        for rec in self.artifact["recommendations"]:
            status = rec["recommendation"]["status"]
            reasons = rec["recommendation"]["reason_ids"]
            if status == "not_recommended":
                self.assertEqual(len(reasons), 0)
            else:
                self.assertGreater(len(reasons), 0)
                # Verify reason validity
                for r in reasons:
                    self.assertIn(r, [
                        "observed_market_demand",
                        "employer_validated",
                        "observed_in_both_sources",
                        "course_coverage_gap",
                        "employer_only_signal"
                    ])

    def test_13_decision_factors(self):
        for rec in self.artifact["recommendations"]:
            df = rec["decision_factors"]
            self.assertIn("market_demand", df)
            self.assertIn("employer_validation", df)
            self.assertIn("course_coverage", df)
            self.assertIn("multi_source_evidence", df)

    def test_14_no_score(self):
        raw_json = json.dumps(self.artifact).lower()
        forbidden = [
            "skill_score", "recommendation_score", "priority_score",
            "employability_score", "market_score", "importance_score", "final_score"
        ]
        for fb in forbidden:
            self.assertNotIn(fb, raw_json)

    def test_15_no_ranking(self):
        rec_ids = [r["skill_id"] for r in self.artifact["recommendations"]]
        self.assertEqual(rec_ids, sorted(rec_ids))

    def test_16_course_isolation(self):
        # Recommendations do not contain course recommendations or course scores
        raw_json = json.dumps(self.artifact).lower()
        self.assertNotIn("recommend_course", raw_json)
        self.assertNotIn("best_course", raw_json)

    def test_17_determinism(self):
        run2 = GenericSkillRecommendationEngine().recommend()
        self.assertEqual(json.dumps(self.artifact, sort_keys=True), json.dumps(run2, sort_keys=True))

    def test_18_all_skills_retained(self):
        self.assertEqual(len(self.artifact["recommendations"]), 35)
        self.assertEqual(
            self.artifact["metadata"]["recommended_skills"] + self.artifact["metadata"]["not_recommended_skills"],
            self.artifact["metadata"]["total_skills"]
        )

    def test_19_no_raw_data(self):
        engine = GenericSkillRecommendationEngine(
            evidence_artifact_path=DEFAULT_EVIDENCE_PATH,
            gap_artifact_path=DEFAULT_GAP_PATH,
            taxonomy_path=DEFAULT_TAXONOMY_PATH
        )
        res = engine.recommend()
        self.assertEqual(res["metadata"]["total_skills"], 35)

    def test_20_source_value_preservation(self):
        with open(DEFAULT_EVIDENCE_PATH, "r", encoding="utf-8") as f:
            ev_data = json.load(f)
        ev_map = {s["skill_id"]: s for s in ev_data["skills"]}

        for rec in self.artifact["recommendations"]:
            sid = rec["skill_id"]
            src_ev = ev_map[sid]
            self.assertEqual(rec["evidence"]["evidence_relationship"], src_ev["evidence_relationship"])
            self.assertEqual(rec["evidence"]["job_demand"], src_ev["job_demand"])
            self.assertEqual(rec["evidence"]["employer_validation"], src_ev["employer_validation"])

if __name__ == "__main__":
    unittest.main()
