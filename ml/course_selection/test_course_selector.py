import unittest
import json
import tempfile
from pathlib import Path
from ml.course_selection.course_selector import (
    CourseCandidateSelector,
    select_course_candidates,
    DEFAULT_RECOMMENDATION_PATH,
    DEFAULT_MAPPING_PATH,
    DEFAULT_COURSE_PATH,
    DEFAULT_TAXONOMY_PATH,
    DEFAULT_OUTPUT_ARTIFACT_PATH
)

class TestCourseCandidateSelector(unittest.TestCase):

    def setUp(self):
        self.selector = CourseCandidateSelector()
        self.result = self.selector.select_candidates()

    def test_01_7c_input_loading(self):
        """TEST 01: Verify Phase 7C personalized recommendations artifact loads correctly."""
        self.assertTrue(DEFAULT_RECOMMENDATION_PATH.exists())
        self.assertIn("students", self.selector.rec_data)
        self.assertEqual(len(self.selector.rec_data["students"]), 5)

    def test_02_7d_input_loading(self):
        """TEST 02: Verify Phase 7D course mapping artifact loads correctly."""
        self.assertTrue(DEFAULT_MAPPING_PATH.exists())
        self.assertIn("students", self.selector.map_data)
        self.assertEqual(len(self.selector.map_data["students"]), 5)

    def test_03_course_catalog_loading(self):
        """TEST 03: Verify sample_courses.json loads correctly."""
        self.assertTrue(DEFAULT_COURSE_PATH.exists())
        self.assertEqual(len(self.selector.course_data), 5)
        course_ids = {c["course_id"] for c in self.selector.course_data}
        self.assertEqual(course_ids, {42, 101, 102, 103, 104})

    def test_04_taxonomy_loading(self):
        """TEST 04: Verify skills.json taxonomy loads correctly."""
        self.assertTrue(DEFAULT_TAXONOMY_PATH.exists())
        self.assertEqual(len(self.selector.tax_data), 68)
        self.assertEqual(len(self.selector.valid_skill_ids), 68)

    def test_05_student_count(self):
        """TEST 05: Verify student count matches Phase 7C (5 students)."""
        self.assertEqual(len(self.result["students"]), 5)
        self.assertEqual(self.result["metadata"]["total_students"], 5)

    def test_06_personalized_skill_count(self):
        """TEST 06: Verify personalized skill universe matches Phase 7C (8 recommendations)."""
        self.assertEqual(self.result["metadata"]["total_personalized_skills"], 8)
        total_recs = sum(len(s["personalized_skill_ids"]) for s in self.result["students"])
        self.assertEqual(total_recs, 8)

    def test_07_only_personalized_skills(self):
        """TEST 07: No already_present or not_recommended skills become course targets."""
        stu_003 = next(s for s in self.result["students"] if s["student_id"] == "STU_003")
        self.assertEqual(stu_003["personalized_skill_ids"], ["SK_SQL"])
        for c in stu_003["candidate_courses"]:
            self.assertEqual(c["covered_personalized_skill_ids"], ["SK_SQL"])
            self.assertNotIn("SK_PYTHON", c["covered_personalized_skill_ids"])
            self.assertNotIn("SK_GIT", c["covered_personalized_skill_ids"])

    def test_08_course_candidate_creation(self):
        """TEST 08: A course becomes a candidate iff it covers at least one personalized skill."""
        for s in self.result["students"]:
            for c in s["candidate_courses"]:
                self.assertGreaterEqual(c["covered_personalized_skill_count"], 1)
                self.assertGreaterEqual(len(c["covered_personalized_skill_ids"]), 1)

    def test_09_multi_skill_course(self):
        """TEST 09: One course can cover multiple personalized skills for a student."""
        stu_002 = next(s for s in self.result["students"] if s["student_id"] == "STU_002")
        self.assertEqual(len(stu_002["candidate_courses"]), 1)
        c42 = stu_002["candidate_courses"][0]
        self.assertEqual(c42["course_id"], 42)
        self.assertEqual(c42["covered_personalized_skill_count"], 2)
        self.assertEqual(c42["covered_personalized_skill_ids"], ["SK_DIAG", "SK_THERMAL"])

    def test_10_multi_course_skill(self):
        """TEST 10: One personalized skill can map to multiple candidate courses."""
        stu_003 = next(s for s in self.result["students"] if s["student_id"] == "STU_003")
        self.assertEqual(len(stu_003["candidate_courses"]), 2)
        c_ids = [c["course_id"] for c in stu_003["candidate_courses"]]
        self.assertEqual(c_ids, [101, 102])
        for c in stu_003["candidate_courses"]:
            self.assertIn("SK_SQL", c["covered_personalized_skill_ids"])

    def test_11_uncovered_skill(self):
        """TEST 11: A personalized skill with no course remains explicitly uncovered."""
        stu_001 = next(s for s in self.result["students"] if s["student_id"] == "STU_001")
        self.assertIn("SK_AWS", stu_001["uncovered_personalized_skills"])

        stu_002 = next(s for s in self.result["students"] if s["student_id"] == "STU_002")
        self.assertIn("SK_CAN", stu_002["uncovered_personalized_skills"])

        stu_004 = next(s for s in self.result["students"] if s["student_id"] == "STU_004")
        self.assertEqual(stu_004["uncovered_personalized_skills"], ["SK_EHR"])

        stu_005 = next(s for s in self.result["students"] if s["student_id"] == "STU_005")
        self.assertEqual(stu_005["uncovered_personalized_skills"], ["SK_SCADA"])

    def test_12_course_deduplication(self):
        """TEST 12: A course appears only once per student in candidate_courses."""
        for s in self.result["students"]:
            course_ids = [c["course_id"] for c in s["candidate_courses"]]
            self.assertEqual(len(course_ids), len(set(course_ids)))

    def test_13_skill_deduplication(self):
        """TEST 13: A personalized skill appears only once per candidate course."""
        for s in self.result["students"]:
            for c in s["candidate_courses"]:
                sk_ids = c["covered_personalized_skill_ids"]
                self.assertEqual(len(sk_ids), len(set(sk_ids)))

    def test_14_course_id_validation(self):
        """TEST 14: Every candidate course exists in sample_courses.json."""
        valid_courses = {c["course_id"] for c in self.selector.course_data}
        for s in self.result["students"]:
            for c in s["candidate_courses"]:
                self.assertIn(c["course_id"], valid_courses)

    def test_15_skill_id_validation(self):
        """TEST 15: Every personalized skill exists in skills.json taxonomy."""
        for s in self.result["students"]:
            for sk in s["personalized_skill_ids"]:
                self.assertIn(sk, self.selector.valid_skill_ids)
            for sk in s["uncovered_personalized_skills"]:
                self.assertIn(sk, self.selector.valid_skill_ids)

    def test_16_role_preservation(self):
        """TEST 16: Student role information matches Phase 7C exactly."""
        rec_roles = {
            s["student_id"]: s["role"]
            for s in self.selector.rec_data["students"]
        }
        for s in self.result["students"]:
            self.assertEqual(s["role"], rec_roles[s["student_id"]])

    def test_17_course_name_preservation(self):
        """TEST 17: Candidate course names match sample_courses.json exactly."""
        course_names = {c["course_id"]: c["name"] for c in self.selector.course_data}
        for s in self.result["students"]:
            for c in s["candidate_courses"]:
                self.assertEqual(c["course_name"], course_names[c["course_id"]])
        for gu in self.result["global_course_usage"]:
            self.assertEqual(gu["course_name"], course_names[gu["course_id"]])

    def test_18_coverage_relationship(self):
        """TEST 18: Every covered skill must actually exist in the candidate course's taught skills."""
        course_skills = {c["course_id"]: set(c.get("skill_ids", [])) for c in self.selector.course_data}
        for s in self.result["students"]:
            for c in s["candidate_courses"]:
                c_id = c["course_id"]
                for sk in c["covered_personalized_skill_ids"]:
                    self.assertIn(sk, course_skills[c_id])

    def test_19_no_false_coverage(self):
        """TEST 19: A course must not claim coverage for skills it does not teach."""
        stu_002 = next(s for s in self.result["students"] if s["student_id"] == "STU_002")
        c42 = next(c for c in stu_002["candidate_courses"] if c["course_id"] == 42)
        self.assertNotIn("SK_CAN", c42["covered_personalized_skill_ids"])

    def test_20_student_summary(self):
        """TEST 20: For every student: covered + uncovered == total personalized skills."""
        for s in self.result["students"]:
            summ = s["summary"]
            self.assertEqual(
                summ["covered_personalized_skill_count"] + summ["uncovered_personalized_skill_count"],
                summ["total_personalized_skills"]
            )
            self.assertEqual(summ["total_personalized_skills"], len(s["personalized_skill_ids"]))
            self.assertEqual(summ["candidate_course_count"], len(s["candidate_courses"]))

    def test_21_candidate_course_count(self):
        """TEST 21: Count unique course IDs across global candidate usage."""
        unique_candidate_courses = {
            c["course_id"]
            for s in self.result["students"]
            for c in s["candidate_courses"]
        }
        self.assertEqual(self.result["metadata"]["total_candidate_courses"], len(unique_candidate_courses))
        self.assertEqual(self.result["metadata"]["total_candidate_courses"], 3)

    def test_22_global_course_usage(self):
        """TEST 22: Candidate-for-student lists in global_course_usage are complete."""
        gu_map = {gu["course_id"]: gu["candidate_for_students"] for gu in self.result["global_course_usage"]}
        self.assertEqual(gu_map[42], ["STU_002"])
        self.assertEqual(gu_map[101], ["STU_003"])
        self.assertEqual(gu_map[102], ["STU_001", "STU_003"])
        self.assertNotIn(103, gu_map)
        self.assertNotIn(104, gu_map)

    def test_23_global_determinism(self):
        """TEST 23: Global mappings are deterministic across repeated runs."""
        r1 = self.selector.select_candidates()
        r2 = self.selector.select_candidates()
        self.assertEqual(r1["global_course_usage"], r2["global_course_usage"])

    def test_24_no_ranking(self):
        """TEST 24: Output must not contain rank, best_course, top_course, winner, priority fields."""
        def check_no_ranking_keys(d):
            if isinstance(d, dict):
                for k, v in d.items():
                    if k in ["rank", "best_course", "top_course", "winner", "priority"]:
                        return False
                    if not check_no_ranking_keys(v):
                        return False
            elif isinstance(d, list):
                for item in d:
                    if not check_no_ranking_keys(item):
                        return False
            return True
        self.assertTrue(check_no_ranking_keys(self.result["students"]))
        self.assertTrue(check_no_ranking_keys(self.result["global_course_usage"]))

    def test_25_no_scores(self):
        """TEST 25: Output must not contain score fields."""
        def check_no_score_keys(d):
            if isinstance(d, dict):
                for k, v in d.items():
                    if k in ["course_score", "fit_score", "relevance_score", "suitability_score", "quality_score", "completeness_score"]:
                        return False
                    if not check_no_score_keys(v):
                        return False
            elif isinstance(d, list):
                for item in d:
                    if not check_no_score_keys(item):
                        return False
            return True
        self.assertTrue(check_no_score_keys(self.result["students"]))
        self.assertTrue(check_no_score_keys(self.result["global_course_usage"]))

    def test_26_no_learning_path(self):
        """TEST 26: Output must not contain learning path or sequencing fields."""
        def check_no_path_keys(d):
            if isinstance(d, dict):
                for k, v in d.items():
                    if k in ["learning_path", "sequence", "prerequisite", "training_plan"]:
                        return False
                    if not check_no_path_keys(v):
                        return False
            elif isinstance(d, list):
                for item in d:
                    if not check_no_path_keys(item):
                        return False
            return True
        self.assertTrue(check_no_path_keys(self.result["students"]))
        self.assertTrue(check_no_path_keys(self.result["global_course_usage"]))

    def test_27_no_new_recommendations(self):
        """TEST 27: 7E cannot create new personalized recommendations; must match 7C exactly."""
        rec_by_student = {
            s["student_id"]: [
                r["skill_id"] for r in s["skill_recommendations"]
                if r.get("personalized_status") == "recommended"
            ]
            for s in self.selector.rec_data["students"]
        }
        for s in self.result["students"]:
            self.assertEqual(sorted(s["personalized_skill_ids"]), sorted(rec_by_student[s["student_id"]]))

    def test_28_no_raw_data(self):
        """TEST 28: Metadata confirms strictly structured upstream artifacts are consumed."""
        meta = self.result["metadata"]
        self.assertTrue(meta["personalized_recommendation_input"].endswith("student_skill_recommendations.json"))
        self.assertTrue(meta["course_mapping_input"].endswith("personalized_course_mapping.json"))
        self.assertTrue(meta["course_catalog_input"].endswith("sample_courses.json"))
        self.assertTrue(meta["taxonomy_input"].endswith("skills.json"))

    def test_29_determinism(self):
        """TEST 29: Repeated execution produces byte-identical JSON."""
        res1 = self.selector.select_candidates()
        res2 = self.selector.select_candidates()
        self.assertEqual(json.dumps(res1, sort_keys=True), json.dumps(res2, sort_keys=True))

    def test_30_sorting(self):
        """TEST 30: Sort students by student_id ASC, skills by skill_id ASC, courses by course_id ASC."""
        stu_ids = [s["student_id"] for s in self.result["students"]]
        self.assertEqual(stu_ids, sorted(stu_ids))

        for s in self.result["students"]:
            self.assertEqual(s["personalized_skill_ids"], sorted(s["personalized_skill_ids"]))
            self.assertEqual(s["uncovered_personalized_skills"], sorted(s["uncovered_personalized_skills"]))
            c_ids = [c["course_id"] for c in s["candidate_courses"]]
            self.assertEqual(c_ids, sorted(c_ids))
            for c in s["candidate_courses"]:
                self.assertEqual(c["covered_personalized_skill_ids"], sorted(c["covered_personalized_skill_ids"]))

        gu_course_ids = [gu["course_id"] for gu in self.result["global_course_usage"]]
        self.assertEqual(gu_course_ids, sorted(gu_course_ids))
        for gu in self.result["global_course_usage"]:
            self.assertEqual(gu["candidate_for_students"], sorted(gu["candidate_for_students"]))

    def test_31_course_immutability(self):
        """TEST 31: sample_courses.json unchanged."""
        with open(DEFAULT_COURSE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data), 5)

    def test_32_taxonomy_immutability(self):
        """TEST 32: skills.json unchanged."""
        with open(DEFAULT_TAXONOMY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data), 68)

    def test_33_error_visibility(self):
        """TEST 33: Invalid skill reference produces visible error in errors list."""
        bad_rec = {
            "students": [
                {
                    "student_id": "STU_TEST",
                    "role": {"role_id": "ROLE_TEST", "role_name": "Tester"},
                    "skill_recommendations": [
                        {"skill_id": "SK_NONEXISTENT", "personalized_status": "recommended"}
                    ]
                }
            ]
        }
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as f:
            json.dump(bad_rec, f)
            temp_path = Path(f.name)

        try:
            selector = CourseCandidateSelector(recommendation_path=temp_path)
            res = selector.select_candidates()
            self.assertEqual(len(res["errors"]), 1)
            self.assertEqual(res["errors"][0]["type"], "UNKNOWN_SKILL_ID")
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_34_expected_synthetic_cases(self):
        """TEST 34: Explicitly verify all 5 synthetic benchmark student expectations."""
        stu_map = {s["student_id"]: s for s in self.result["students"]}

        # STU_001
        s1 = stu_map["STU_001"]
        self.assertEqual(s1["personalized_skill_ids"], ["SK_AIRFLOW", "SK_AWS"])
        self.assertEqual(len(s1["candidate_courses"]), 1)
        self.assertEqual(s1["candidate_courses"][0]["course_id"], 102)
        self.assertEqual(s1["candidate_courses"][0]["covered_personalized_skill_ids"], ["SK_AIRFLOW"])
        self.assertEqual(s1["uncovered_personalized_skills"], ["SK_AWS"])

        # STU_002
        s2 = stu_map["STU_002"]
        self.assertEqual(s2["personalized_skill_ids"], ["SK_CAN", "SK_DIAG", "SK_THERMAL"])
        self.assertEqual(len(s2["candidate_courses"]), 1)
        self.assertEqual(s2["candidate_courses"][0]["course_id"], 42)
        self.assertEqual(s2["candidate_courses"][0]["covered_personalized_skill_ids"], ["SK_DIAG", "SK_THERMAL"])
        self.assertEqual(s2["uncovered_personalized_skills"], ["SK_CAN"])

        # STU_003
        s3 = stu_map["STU_003"]
        self.assertEqual(s3["personalized_skill_ids"], ["SK_SQL"])
        self.assertEqual(len(s3["candidate_courses"]), 2)
        self.assertEqual(s3["candidate_courses"][0]["course_id"], 101)
        self.assertEqual(s3["candidate_courses"][0]["covered_personalized_skill_ids"], ["SK_SQL"])
        self.assertEqual(s3["candidate_courses"][1]["course_id"], 102)
        self.assertEqual(s3["candidate_courses"][1]["covered_personalized_skill_ids"], ["SK_SQL"])
        self.assertEqual(s3["uncovered_personalized_skills"], [])

        # STU_004
        s4 = stu_map["STU_004"]
        self.assertEqual(s4["personalized_skill_ids"], ["SK_EHR"])
        self.assertEqual(len(s4["candidate_courses"]), 0)
        self.assertEqual(s4["uncovered_personalized_skills"], ["SK_EHR"])

        # STU_005
        s5 = stu_map["STU_005"]
        self.assertEqual(s5["personalized_skill_ids"], ["SK_SCADA"])
        self.assertEqual(len(s5["candidate_courses"]), 0)
        self.assertEqual(s5["uncovered_personalized_skills"], ["SK_SCADA"])

if __name__ == "__main__":
    unittest.main()
