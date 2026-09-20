import unittest
import json
from pathlib import Path
from ml.evidence.evidence_aggregator import (
    MultiSignalEvidenceAggregator,
    DEFAULT_DEMAND_PATH,
    DEFAULT_EMPLOYER_PATH,
    DEFAULT_TAXONOMY_PATH
)

class TestMultiSignalEvidenceAggregator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.aggregator = MultiSignalEvidenceAggregator()
        cls.artifact = cls.aggregator.aggregate()

    def test_01_phase3_input_loads(self):
        with open(DEFAULT_DEMAND_PATH, "r", encoding="utf-8") as f:
            d_data = json.load(f)
        self.assertEqual(self.artifact["metadata"]["job_dataset_skill_count"], len(d_data["skills"]))
        self.assertEqual(self.artifact["metadata"]["job_dataset_total_jobs"], d_data["metadata"]["total_jobs"])

    def test_02_phase5a_input_loads(self):
        with open(DEFAULT_EMPLOYER_PATH, "r", encoding="utf-8") as f:
            e_data = json.load(f)
        self.assertEqual(self.artifact["metadata"]["employer_feedback_skill_count"], len(e_data["skill_signals"]))
        self.assertEqual(self.artifact["metadata"]["employer_feedback_total_records"], e_data["metadata"]["total_feedback_records"])

    def test_03_taxonomy_validation(self):
        with open(DEFAULT_TAXONOMY_PATH, "r", encoding="utf-8") as f:
            tax = json.load(f)
        valid_ids = {s["id"] for s in tax}
        for s in self.artifact["skills"]:
            self.assertIn(s["skill_id"], valid_ids)

    def test_04_union_skill_count(self):
        self.assertEqual(self.artifact["metadata"]["union_skill_count"], 35)
        self.assertEqual(len(self.artifact["skills"]), 35)
        self.assertEqual(len(self.artifact["evidence_matrix"]), 35)

    def test_05_job_only_skills(self):
        aws_entry = next(s for s in self.artifact["skills"] if s["skill_id"] == "SK_AWS")
        self.assertEqual(aws_entry["evidence_relationship"], "job_only")
        self.assertEqual(aws_entry["evidence_sources"], ["job_postings"])
        self.assertTrue(aws_entry["job_demand"]["observed"])
        self.assertEqual(aws_entry["job_demand"]["job_count"], 51)
        self.assertFalse(aws_entry["employer_validation"]["observed"])
        self.assertIsNone(aws_entry["employer_validation"]["feedback_count"])
        self.assertIsNone(aws_entry["employer_validation"]["unique_employer_count"])
        self.assertIsNone(aws_entry["employer_validation"]["weighted_signal_sum"])

    def test_06_employer_only_skills(self):
        can_entry = next(s for s in self.artifact["skills"] if s["skill_id"] == "SK_CAN")
        self.assertEqual(can_entry["evidence_relationship"], "employer_feedback_only")
        self.assertEqual(can_entry["evidence_sources"], ["employer_feedback"])
        self.assertFalse(can_entry["job_demand"]["observed"])
        self.assertIsNone(can_entry["job_demand"]["job_count"])
        self.assertIsNone(can_entry["job_demand"]["demand_share"])
        self.assertTrue(can_entry["employer_validation"]["observed"])
        self.assertEqual(can_entry["employer_validation"]["feedback_count"], 3)
        self.assertEqual(can_entry["employer_validation"]["unique_employer_count"], 3)

    def test_07_both_sources_skills(self):
        py_entry = next(s for s in self.artifact["skills"] if s["skill_id"] == "SK_PYTHON")
        self.assertEqual(py_entry["evidence_relationship"], "both")
        self.assertEqual(set(py_entry["evidence_sources"]), {"job_postings", "employer_feedback"})
        self.assertTrue(py_entry["job_demand"]["observed"])
        self.assertTrue(py_entry["employer_validation"]["observed"])
        self.assertEqual(py_entry["job_demand"]["job_count"], 98)
        self.assertEqual(py_entry["employer_validation"]["feedback_count"], 1)

    def test_08_value_preservation(self):
        with open(DEFAULT_DEMAND_PATH, "r", encoding="utf-8") as f:
            d_data = json.load(f)
        with open(DEFAULT_EMPLOYER_PATH, "r", encoding="utf-8") as f:
            e_data = json.load(f)

        d_map = {s["skill_id"]: s for s in d_data["skills"]}
        e_map = {s["skill_id"]: s for s in e_data["skill_signals"]}

        for s in self.artifact["skills"]:
            sid = s["skill_id"]
            if sid in d_map:
                self.assertEqual(s["job_demand"]["job_count"], d_map[sid]["job_count"])
                self.assertEqual(s["job_demand"]["demand_share"], d_map[sid]["demand_share"])
            if sid in e_map:
                self.assertEqual(s["employer_validation"]["feedback_count"], e_map[sid]["feedback_count"])
                self.assertEqual(s["employer_validation"]["weighted_signal_sum"], e_map[sid]["weighted_signal_sum"])

    def test_09_relationship_assignment(self):
        both_ids = {"SK_AIRFLOW", "SK_BMS", "SK_PYTHON", "SK_SQL"}
        for s in self.artifact["skills"]:
            sid = s["skill_id"]
            if sid in both_ids:
                self.assertEqual(s["evidence_relationship"], "both")
            elif s["job_demand"]["observed"]:
                self.assertEqual(s["evidence_relationship"], "job_only")
            else:
                self.assertEqual(s["evidence_relationship"], "employer_feedback_only")

    def test_10_evidence_matrix(self):
        mat = self.artifact["evidence_matrix"]
        self.assertEqual(len(mat), 35)
        for entry in mat:
            self.assertIn("skill_id", entry)
            self.assertIn("job_postings", entry)
            self.assertIn("employer_feedback", entry)

    def test_11_no_combined_score(self):
        raw_json = json.dumps(self.artifact).lower()
        forbidden = ["combined_score", "priority_score", "importance_score", "recommendation_score", "opportunity_score"]
        for fb in forbidden:
            self.assertNotIn(fb, raw_json)

    def test_12_course_isolation(self):
        raw_json = json.dumps(self.artifact).lower()
        self.assertNotIn("gap_analysis", raw_json)
        self.assertNotIn("sample_courses", raw_json)

    def test_13_no_raw_data_dependency(self):
        agg = MultiSignalEvidenceAggregator(
            demand_artifact_path=DEFAULT_DEMAND_PATH,
            employer_artifact_path=DEFAULT_EMPLOYER_PATH,
            taxonomy_path=DEFAULT_TAXONOMY_PATH
        )
        res = agg.aggregate()
        self.assertEqual(res["metadata"]["union_skill_count"], 35)

    def test_14_determinism(self):
        run2 = MultiSignalEvidenceAggregator().aggregate()
        self.assertEqual(json.dumps(self.artifact, sort_keys=True), json.dumps(run2, sort_keys=True))

    def test_15_source_counts(self):
        meta = self.artifact["metadata"]
        self.assertEqual(meta["job_dataset_skill_count"], 30)
        self.assertEqual(meta["employer_feedback_skill_count"], 9)
        self.assertEqual(meta["both_sources_skill_count"], 4)
        self.assertEqual(meta["job_only_skill_count"], 26)
        self.assertEqual(meta["employer_only_skill_count"], 5)
        self.assertEqual(
            meta["both_sources_skill_count"] + meta["job_only_skill_count"] + meta["employer_only_skill_count"],
            meta["union_skill_count"]
        )

    def test_16_null_semantics(self):
        # Verify that unobserved values are strictly None/null, NOT 0
        for s in self.artifact["skills"]:
            if not s["job_demand"]["observed"]:
                self.assertIsNone(s["job_demand"]["job_count"])
                self.assertIsNone(s["job_demand"]["demand_percentage"])
            if not s["employer_validation"]["observed"]:
                self.assertIsNone(s["employer_validation"]["feedback_count"])
                self.assertIsNone(s["employer_validation"]["weighted_signal_sum"])

if __name__ == "__main__":
    unittest.main()
