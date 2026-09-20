import unittest
import json
from pathlib import Path
from ml.gap.gap_analyzer import SkillGapAnalyzer, DEFAULT_DEMAND_PATH, DEFAULT_COURSES_PATH, DEFAULT_TAXONOMY_PATH

class TestSkillGapAnalyzer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analyzer = SkillGapAnalyzer()
        cls.artifact = cls.analyzer.analyze()

    def test_01_input_integrity(self):
        with open(DEFAULT_DEMAND_PATH, "r", encoding="utf-8") as f:
            demand_data = json.load(f)
        self.assertEqual(self.artifact["metadata"]["observed_demand_skills"], len(demand_data["skills"]))
        self.assertEqual(self.artifact["metadata"]["total_observed_demand"], sum(s["job_count"] for s in demand_data["skills"]))
        self.assertEqual(self.artifact["metadata"]["observed_demand_skills"], 30)
        self.assertEqual(self.artifact["metadata"]["total_observed_demand"], 536)

    def test_02_course_input(self):
        with open(DEFAULT_COURSES_PATH, "r", encoding="utf-8") as f:
            courses_data = json.load(f)
        self.assertEqual(len(self.artifact["courses"]), len(courses_data))
        self.assertEqual(self.artifact["metadata"]["total_courses"], 5)
        course_ids = [c["course_id"] for c in self.artifact["courses"]]
        self.assertEqual(course_ids, [42, 101, 102, 103, 104])

    def test_03_taxonomy_validation(self):
        with open(DEFAULT_TAXONOMY_PATH, "r", encoding="utf-8") as f:
            tax = json.load(f)
        valid_ids = {s["id"] for s in tax}
        for c in self.artifact["courses"]:
            for sid in c["course_skills"]:
                self.assertIn(sid, valid_ids)

    def test_04_demand_universe(self):
        with open(DEFAULT_DEMAND_PATH, "r", encoding="utf-8") as f:
            demand_data = json.load(f)
        demand_ids = {s["skill_id"] for s in demand_data["skills"]}
        for c in self.artifact["courses"]:
            self.assertEqual(c["observed_demand_skill_count"], len(demand_ids))
            for s in c["covered_skills"]:
                self.assertIn(s["skill_id"], demand_ids)
            for s in c["missing_skills"]:
                self.assertIn(s["skill_id"], demand_ids)

    def test_05_covered_skill(self):
        c101 = next(c for c in self.artifact["courses"] if c["course_id"] == 101)
        covered_ids = {s["skill_id"] for s in c101["covered_skills"]}
        self.assertIn("SK_PYTHON", covered_ids)
        self.assertIn("SK_SQL", covered_ids)
        self.assertIn("SK_GIT", covered_ids)
        self.assertIn("SK_DOCKER", covered_ids)
        self.assertIn("SK_FASTAPI", covered_ids)

    def test_06_missing_skill(self):
        c101 = next(c for c in self.artifact["courses"] if c["course_id"] == 101)
        missing_ids = {s["skill_id"] for s in c101["missing_skills"]}
        self.assertIn("SK_AWS", missing_ids)
        self.assertNotIn("SK_PYTHON", missing_ids)

    def test_07_job_based_demand(self):
        c101 = next(c for c in self.artifact["courses"] if c["course_id"] == 101)
        py_entry = next(s for s in c101["covered_skills"] if s["skill_id"] == "SK_PYTHON")
        self.assertEqual(py_entry["job_count"], 98)

    def test_08_demand_coverage(self):
        total_demand = self.artifact["metadata"]["total_observed_demand"]
        for c in self.artifact["courses"]:
            self.assertEqual(c["covered_demand"] + c["missing_demand"], total_demand)
            expected_ratio = round(c["covered_demand"] / total_demand, 4)
            self.assertEqual(c["demand_coverage_ratio"], expected_ratio)

    def test_09_skill_coverage(self):
        for c in self.artifact["courses"]:
            total_skills = c["observed_demand_skill_count"]
            self.assertEqual(c["covered_demand_skill_count"] + c["missing_demand_skill_count"], total_skills)
            expected_ratio = round(c["covered_demand_skill_count"] / total_skills, 4)
            self.assertEqual(c["skill_coverage_ratio"], expected_ratio)

    def test_10_zero_demand(self):
        # Edge test with zero demand
        empty_demand = {"metadata": {"total_jobs": 0}, "skills": []}
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(empty_demand, f)
            temp_path = Path(f.name)
        try:
            analyzer = SkillGapAnalyzer(demand_artifact_path=temp_path)
            res = analyzer.analyze()
            for c in res["courses"]:
                self.assertEqual(c["demand_coverage_ratio"], 0.0)
                self.assertEqual(c["skill_coverage_ratio"], 0.0)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_11_out_of_demand_course_skills(self):
        c42 = next(c for c in self.artifact["courses"] if c["course_id"] == 42)
        out_ids = {s["skill_id"] for s in c42["course_skills_without_observed_demand"]}
        self.assertIn("SK_DIAG", out_ids)
        self.assertIn("SK_THERMAL", out_ids)
        # Verify out of demand skills are not in missing skills
        missing_ids = {s["skill_id"] for s in c42["missing_skills"]}
        self.assertNotIn("SK_DIAG", missing_ids)
        self.assertNotIn("SK_THERMAL", missing_ids)

    def test_12_global_coverage(self):
        total_courses = self.artifact["metadata"]["total_courses"]
        for g in self.artifact["global_skill_gap"]:
            self.assertEqual(g["courses_covering"] + g["courses_missing"], total_courses)

    def test_13_determinism(self):
        run2 = SkillGapAnalyzer().analyze()
        self.assertEqual(json.dumps(self.artifact, sort_keys=True), json.dumps(run2, sort_keys=True))

    def test_14_no_recommendation_logic(self):
        raw_json = json.dumps(self.artifact).lower()
        forbidden = ["recommend", "should add", "suggest", "actionable", "must teach"]
        for fb in forbidden:
            self.assertNotIn(fb, raw_json)

    def test_15_no_raw_data_dependency(self):
        # Verify analyzer initializes and runs purely from Phase 3 demand & sample_courses
        analyzer = SkillGapAnalyzer(
            demand_artifact_path=DEFAULT_DEMAND_PATH,
            courses_path=DEFAULT_COURSES_PATH,
            taxonomy_path=DEFAULT_TAXONOMY_PATH
        )
        res = analyzer.analyze()
        self.assertEqual(res["metadata"]["total_courses"], 5)

if __name__ == "__main__":
    unittest.main()
