import unittest
import json
from pathlib import Path
from ml.personalized.personalized_recommender import (
    PersonalizedSkillRecommendationEngine,
    DEFAULT_GAP_INPUT_PATH,
    DEFAULT_RECOMMENDATION_PATH,
    DEFAULT_CONTEXT_PATH,
    DEFAULT_EVIDENCE_PATH,
    DEFAULT_TAXONOMY_PATH
)

class TestPersonalizedSkillRecommendationEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = PersonalizedSkillRecommendationEngine()
        cls.artifact = cls.engine.recommend()

    def test_01_gap_input(self):
        with open(DEFAULT_GAP_INPUT_PATH, "r", encoding="utf-8") as f:
            gaps = json.load(f)
        self.assertEqual(len(self.artifact["students"]), len(gaps["students"]))

    def test_02_generic_recommendations_input(self):
        with open(DEFAULT_RECOMMENDATION_PATH, "r", encoding="utf-8") as f:
            rec = json.load(f)
        self.assertGreater(len(rec["recommendations"]), 0)

    def test_03_context_input(self):
        with open(DEFAULT_CONTEXT_PATH, "r", encoding="utf-8") as f:
            ctx = json.load(f)
        self.assertGreater(len(ctx["roles"]), 0)

    def test_04_evidence_input(self):
        with open(DEFAULT_EVIDENCE_PATH, "r", encoding="utf-8") as f:
            ev = json.load(f)
        self.assertGreater(len(ev["skills"]), 0)

    def test_05_taxonomy_input(self):
        with open(DEFAULT_TAXONOMY_PATH, "r", encoding="utf-8") as f:
            tax = json.load(f)
        valid_ids = {s["id"] for s in tax}
        for s in self.artifact["students"]:
            for r in s["skill_recommendations"]:
                self.assertIn(r["skill_id"], valid_ids)

    def test_06_student_count(self):
        self.assertEqual(len(self.artifact["students"]), 5)
        self.assertEqual(self.artifact["metadata"]["total_students"], 5)

    def test_07_role_skill_count(self):
        with open(DEFAULT_GAP_INPUT_PATH, "r", encoding="utf-8") as f:
            gaps = json.load(f)
        gap_counts = {s["student_id"]: len(s["skill_gaps"]) for s in gaps["students"]}
        for s in self.artifact["students"]:
            self.assertEqual(len(s["skill_recommendations"]), gap_counts[s["student_id"]])

    def test_08_present_status(self):
        # STU_001 has Python and SQL present -> already_present
        stu1 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_001")
        py_rec = next(r for r in stu1["skill_recommendations"] if r["skill_id"] == "SK_PYTHON")
        self.assertEqual(py_rec["personalized_status"], "already_present")
        self.assertEqual(py_rec["recommendation_reason_ids"], ["already_present"])
        self.assertIn("SK_PYTHON", stu1["already_present_skills"])

    def test_09_missing_plus_generic_recommended(self):
        # STU_001 is missing SK_AWS, which is generic recommended -> recommended
        stu1 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_001")
        aws_rec = next(r for r in stu1["skill_recommendations"] if r["skill_id"] == "SK_AWS")
        self.assertEqual(aws_rec["personalized_status"], "recommended")
        self.assertIn("SK_AWS", stu1["recommended_skills"])
        self.assertIn("generic_evidence_recommended", aws_rec["recommendation_reason_ids"])

    def test_10_missing_plus_generic_not_recommended(self):
        # STU_001 is missing SK_SPARK, which is generic not_recommended -> not_recommended
        stu1 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_001")
        spark_rec = next(r for r in stu1["skill_recommendations"] if r["skill_id"] == "SK_SPARK")
        self.assertEqual(spark_rec["personalized_status"], "not_recommended")
        self.assertIn("SK_SPARK", stu1["not_recommended_skills"])
        self.assertNotIn("generic_evidence_recommended", spark_rec["recommendation_reason_ids"])

    def test_11_missing_plus_context_unavailable(self):
        # STU_005 is missing SK_PANEL_WIRING, which has not_available context -> not_recommended
        stu5 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_005")
        panel_rec = next(r for r in stu5["skill_recommendations"] if r["skill_id"] == "SK_PANEL_WIRING")
        self.assertEqual(panel_rec["personalized_status"], "not_recommended")
        self.assertIn("SK_PANEL_WIRING", stu5["not_recommended_skills"])
        self.assertIn("contextual_evidence_unavailable", panel_rec["recommendation_reason_ids"])

    def test_12_role_requirement(self):
        for s in self.artifact["students"]:
            for r in s["skill_recommendations"]:
                if r["student_status"] == "missing":
                    self.assertIn("role_requirement", r["recommendation_reason_ids"])

    def test_13_student_gap_reason(self):
        for s in self.artifact["students"]:
            for r in s["skill_recommendations"]:
                if r["student_status"] == "missing":
                    self.assertIn("student_skill_gap", r["recommendation_reason_ids"])
                else:
                    self.assertNotIn("student_skill_gap", r["recommendation_reason_ids"])

    def test_14_market_reason(self):
        # Airflow has market demand -> market_demand_evidence
        stu1 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_001")
        airflow_rec = next(r for r in stu1["skill_recommendations"] if r["skill_id"] == "SK_AIRFLOW")
        self.assertIn("market_demand_evidence", airflow_rec["recommendation_reason_ids"])

        # CAN has employer only -> no market_demand_evidence
        stu2 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_002")
        can_rec = next(r for r in stu2["skill_recommendations"] if r["skill_id"] == "SK_CAN")
        self.assertNotIn("market_demand_evidence", can_rec["recommendation_reason_ids"])

    def test_15_employer_reason(self):
        # CAN has employer validation -> employer_validation_evidence
        stu2 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_002")
        can_rec = next(r for r in stu2["skill_recommendations"] if r["skill_id"] == "SK_CAN")
        self.assertIn("employer_validation_evidence", can_rec["recommendation_reason_ids"])

        # AWS has market only -> no employer_validation_evidence
        stu1 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_001")
        aws_rec = next(r for r in stu1["skill_recommendations"] if r["skill_id"] == "SK_AWS")
        self.assertNotIn("employer_validation_evidence", aws_rec["recommendation_reason_ids"])

    def test_16_multi_source_reason(self):
        # Airflow is observed in both -> multi_source_evidence
        stu1 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_001")
        airflow_rec = next(r for r in stu1["skill_recommendations"] if r["skill_id"] == "SK_AIRFLOW")
        self.assertIn("multi_source_evidence", airflow_rec["recommendation_reason_ids"])

        # AWS is job_only -> no multi_source_evidence
        aws_rec = next(r for r in stu1["skill_recommendations"] if r["skill_id"] == "SK_AWS")
        self.assertNotIn("multi_source_evidence", aws_rec["recommendation_reason_ids"])

    def test_17_course_gap_reason(self):
        # AWS has course coverage gap -> course_coverage_gap
        stu1 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_001")
        aws_rec = next(r for r in stu1["skill_recommendations"] if r["skill_id"] == "SK_AWS")
        self.assertIn("course_coverage_gap", aws_rec["recommendation_reason_ids"])

        # Airflow is covered in courses -> no course_coverage_gap
        airflow_rec = next(r for r in stu1["skill_recommendations"] if r["skill_id"] == "SK_AIRFLOW")
        self.assertNotIn("course_coverage_gap", airflow_rec["recommendation_reason_ids"])

    def test_18_already_present_reason(self):
        for s in self.artifact["students"]:
            for r in s["skill_recommendations"]:
                if r["personalized_status"] == "already_present":
                    self.assertEqual(r["recommendation_reason_ids"], ["already_present"])

    def test_19_evidence_preservation(self):
        with open(DEFAULT_EVIDENCE_PATH, "r", encoding="utf-8") as f:
            ev_data = json.load(f)
        ev_map = {s["skill_id"]: s for s in ev_data["skills"]}
        for s in self.artifact["students"]:
            for r in s["skill_recommendations"]:
                sid = r["skill_id"]
                if sid in ev_map:
                    self.assertEqual(r["evidence"]["job_demand"], ev_map[sid]["job_demand"])
                    self.assertEqual(r["evidence"]["employer_validation"], ev_map[sid]["employer_validation"])

    def test_20_generic_reason_preservation(self):
        with open(DEFAULT_RECOMMENDATION_PATH, "r", encoding="utf-8") as f:
            rec_data = json.load(f)
        rec_map = {s["skill_id"]: s["recommendation"]["reason_ids"] for s in rec_data["recommendations"]}
        for s in self.artifact["students"]:
            for r in s["skill_recommendations"]:
                sid = r["skill_id"]
                if sid in rec_map:
                    self.assertEqual(r["generic_recommendation"]["reason_ids"], rec_map[sid])

    def test_21_context_preservation(self):
        for s in self.artifact["students"]:
            for r in s["skill_recommendations"]:
                self.assertIn(r["context"]["contextual_recommendation_status"], ["recommended", "not_recommended", "not_available"])

    def test_22_no_score(self):
        raw_json = json.dumps(self.artifact).lower()
        forbidden = [
            "personalized_score", "recommendation_score", "priority_score",
            "learning_priority", "urgency_score", "gap_score",
            "role_fit_score", "readiness_score", "match_percent"
        ]
        for fb in forbidden:
            self.assertNotIn(fb, raw_json)

    def test_23_no_course_recommendation(self):
        raw_json = json.dumps(self.artifact).lower()
        forbidden = ["course_recommendation", "recommended_course", "learning_path"]
        for fb in forbidden:
            self.assertNotIn(fb, raw_json)

    def test_24_no_proficiency_judgment(self):
        # STU_002 has SK_BMS with basic evidence; still already_present, not recommended
        stu2 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_002")
        bms_rec = next(r for r in stu2["skill_recommendations"] if r["skill_id"] == "SK_BMS")
        self.assertEqual(bms_rec["personalized_status"], "already_present")
        self.assertEqual(bms_rec["recommendation_reason_ids"], ["already_present"])

    def test_25_all_role_skills_retained(self):
        with open(DEFAULT_GAP_INPUT_PATH, "r", encoding="utf-8") as f:
            gaps = json.load(f)
        for g_stu in gaps["students"]:
            sid = g_stu["student_id"]
            p_stu = next(s for s in self.artifact["students"] if s["student_id"] == sid)
            g_sids = {g["skill_id"] for g in g_stu["skill_gaps"]}
            p_sids = {r["skill_id"] for r in p_stu["skill_recommendations"]}
            self.assertEqual(g_sids, p_sids)

    def test_26_summary_counts(self):
        for s in self.artifact["students"]:
            summary = s["summary"]
            rec_cnt = len(s["recommended_skills"])
            pres_cnt = len(s["already_present_skills"])
            not_rec_cnt = len(s["not_recommended_skills"])
            total = len(s["skill_recommendations"])

            self.assertEqual(summary["recommended_skill_count"], rec_cnt)
            self.assertEqual(summary["already_present_count"], pres_cnt)
            self.assertEqual(summary["not_recommended_missing_count"], not_rec_cnt)
            self.assertEqual(summary["total_role_skills"], total)
            self.assertEqual(total, rec_cnt + pres_cnt + not_rec_cnt)

    def test_27_determinism(self):
        run2 = PersonalizedSkillRecommendationEngine().recommend()
        self.assertEqual(json.dumps(self.artifact, sort_keys=True), json.dumps(run2, sort_keys=True))

    def test_28_no_raw_data(self):
        engine = PersonalizedSkillRecommendationEngine(
            student_gap_path=DEFAULT_GAP_INPUT_PATH,
            recommendation_path=DEFAULT_RECOMMENDATION_PATH,
            context_path=DEFAULT_CONTEXT_PATH,
            evidence_path=DEFAULT_EVIDENCE_PATH,
            taxonomy_path=DEFAULT_TAXONOMY_PATH
        )
        res = engine.recommend()
        self.assertEqual(res["metadata"]["total_students"], 5)

    def test_29_no_ranking(self):
        for s in self.artifact["students"]:
            rec_ids = [r["skill_id"] for r in s["skill_recommendations"]]
            self.assertEqual(rec_ids, sorted(rec_ids))

    def test_30_recommended_list_consistency(self):
        for s in self.artifact["students"]:
            for sid in s["recommended_skills"]:
                rec = next(r for r in s["skill_recommendations"] if r["skill_id"] == sid)
                self.assertEqual(rec["personalized_status"], "recommended")

    def test_31_present_list_consistency(self):
        for s in self.artifact["students"]:
            for sid in s["already_present_skills"]:
                rec = next(r for r in s["skill_recommendations"] if r["skill_id"] == sid)
                self.assertEqual(rec["personalized_status"], "already_present")

    def test_32_not_recommended_list_consistency(self):
        for s in self.artifact["students"]:
            for sid in s["not_recommended_skills"]:
                rec = next(r for r in s["skill_recommendations"] if r["skill_id"] == sid)
                self.assertEqual(rec["personalized_status"], "not_recommended")

if __name__ == "__main__":
    unittest.main()
