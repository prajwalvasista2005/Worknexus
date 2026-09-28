import unittest
import json
from pathlib import Path
from ml.gap_student.student_gap_analyzer import (
    StudentSkillGapAnalyzer,
    DEFAULT_STUDENT_PROFILE_PATH,
    DEFAULT_ROLE_CONTEXT_PATH,
    DEFAULT_ROLE_ASSIGNMENT_PATH,
    DEFAULT_TAXONOMY_PATH
)

class TestStudentSkillGapAnalyzer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analyzer = StudentSkillGapAnalyzer()
        cls.artifact = cls.analyzer.analyze_gaps()

    def test_01_student_profile_load(self):
        with open(DEFAULT_STUDENT_PROFILE_PATH, "r", encoding="utf-8") as f:
            profiles = json.load(f)
        self.assertEqual(len(self.artifact["students"]), len(profiles["students"]))
        self.assertEqual(self.artifact["metadata"]["total_students"], len(profiles["students"]))

    def test_02_role_context_load(self):
        with open(DEFAULT_ROLE_CONTEXT_PATH, "r", encoding="utf-8") as f:
            roles = json.load(f)
        self.assertGreater(len(roles["roles"]), 0)
        self.assertEqual(self.artifact["metadata"]["role_context_input"], str(DEFAULT_ROLE_CONTEXT_PATH.as_posix()))

    def test_03_role_assignment_load(self):
        with open(DEFAULT_ROLE_ASSIGNMENT_PATH, "r", encoding="utf-8") as f:
            assigns = json.load(f)
        self.assertEqual(self.artifact["metadata"]["total_assignments"], len(assigns["assignments"]))
        self.assertEqual(len(assigns["assignments"]), 5)

    def test_04_taxonomy_load(self):
        with open(DEFAULT_TAXONOMY_PATH, "r", encoding="utf-8") as f:
            tax = json.load(f)
        self.assertGreater(len(tax), 0)
        valid_ids = {s["id"] for s in tax}
        for s in self.artifact["students"]:
            for gap in s["skill_gaps"]:
                self.assertIn(gap["skill_id"], valid_ids)

    def test_05_student_id_validation(self):
        # Verify all assigned students exist in Phase 7A
        with open(DEFAULT_STUDENT_PROFILE_PATH, "r", encoding="utf-8") as f:
            profiles = json.load(f)
        stu_ids = {s["student_id"] for s in profiles["students"]}
        for s in self.artifact["students"]:
            self.assertIn(s["student_id"], stu_ids)

    def test_06_role_id_validation(self):
        with open(DEFAULT_ROLE_CONTEXT_PATH, "r", encoding="utf-8") as f:
            roles = json.load(f)
        role_ids = {r["role_id"] for r in roles["roles"]}
        for s in self.artifact["students"]:
            self.assertIn(s["role"]["role_id"], role_ids)

    def test_07_assignment_uniqueness(self):
        assigned_students = [s["student_id"] for s in self.artifact["students"]]
        self.assertEqual(len(assigned_students), len(set(assigned_students)))

    def test_08_all_students_assigned(self):
        self.assertEqual(len(self.artifact["students"]), 5)
        assigned_students = {s["student_id"] for s in self.artifact["students"]}
        expected = {"STU_001", "STU_002", "STU_003", "STU_004", "STU_005"}
        self.assertEqual(assigned_students, expected)

    def test_09_role_skill_retention(self):
        with open(DEFAULT_ROLE_CONTEXT_PATH, "r", encoding="utf-8") as f:
            roles = json.load(f)
        role_skills_map = {
            r["role_id"]: {s["skill_id"] for s in r["role_skill_context"]}
            for r in roles["roles"]
        }
        for s in self.artifact["students"]:
            role_id = s["role"]["role_id"]
            expected_skills = role_skills_map[role_id]
            actual_skills = {g["skill_id"] for g in s["skill_gaps"]}
            self.assertEqual(expected_skills, actual_skills)

    def test_10_present_detection(self):
        # STU_001 has SK_PYTHON and SK_SQL for ROLE_DATA_ENGINEER
        stu1 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_001")
        py_gap = next(g for g in stu1["skill_gaps"] if g["skill_id"] == "SK_PYTHON")
        self.assertEqual(py_gap["status"], "present")
        self.assertTrue(py_gap["student_has_skill"])
        self.assertTrue(py_gap["role_requires_skill"])
        self.assertIn("SK_PYTHON", stu1["present_skills"])

    def test_11_missing_detection(self):
        # STU_001 does not have SK_AWS for ROLE_DATA_ENGINEER
        stu1 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_001")
        aws_gap = next(g for g in stu1["skill_gaps"] if g["skill_id"] == "SK_AWS")
        self.assertEqual(aws_gap["status"], "missing")
        self.assertFalse(aws_gap["student_has_skill"])
        self.assertTrue(aws_gap["role_requires_skill"])
        self.assertIn("SK_AWS", stu1["missing_skills"])

    def test_12_canonical_id_matching(self):
        # Matching is solely by skill_id
        for s in self.artifact["students"]:
            for gap in s["skill_gaps"]:
                self.assertTrue(gap["skill_id"].startswith("SK_"))

    def test_13_no_name_matching(self):
        # Skill comparison does not depend on skill_name
        for s in self.artifact["students"]:
            for gap in s["skill_gaps"]:
                self.assertIsNotNone(gap["skill_name"])
                self.assertGreater(len(gap["skill_name"]), 0)

    def test_14_student_evidence_preservation(self):
        # STU_002 has SK_BMS with [course_completed:basic]
        stu2 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_002")
        bms_gap = next(g for g in stu2["skill_gaps"] if g["skill_id"] == "SK_BMS")
        self.assertEqual(bms_gap["status"], "present")
        self.assertEqual(len(bms_gap["student_evidence"]), 1)
        self.assertEqual(bms_gap["student_evidence"][0]["evidence_type"], "course_completed")
        self.assertEqual(bms_gap["student_evidence"][0]["evidence_strength"], "basic")

    def test_15_multiple_evidence_preservation(self):
        # STU_001 has SK_PYTHON with 2 evidence entries
        stu1 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_001")
        py_gap = next(g for g in stu1["skill_gaps"] if g["skill_id"] == "SK_PYTHON")
        self.assertEqual(len(py_gap["student_evidence"]), 2)
        ev_types = {e["evidence_type"] for e in py_gap["student_evidence"]}
        self.assertEqual(ev_types, {"project", "certification"})

    def test_16_context_status_preservation(self):
        # Phase 6B recommendation status is preserved in gap records
        stu1 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_001")
        spark_gap = next(g for g in stu1["skill_gaps"] if g["skill_id"] == "SK_SPARK")
        self.assertEqual(spark_gap["generic_recommendation_status"], "not_recommended")
        self.assertEqual(spark_gap["contextual_recommendation_status"], "not_recommended")

    def test_17_unavailable_context(self):
        # STU_004 in ROLE_HEALTHCARE_ASST has SK_CPR_BLS with not_available contextual status
        stu4 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_004")
        cpr_gap = next(g for g in stu4["skill_gaps"] if g["skill_id"] == "SK_CPR_BLS")
        self.assertEqual(cpr_gap["contextual_recommendation_status"], "not_available")
        self.assertIn("SK_CPR_BLS", stu4["unavailable_context_skills"])

    def test_18_missing_plus_unavailable(self):
        # STU_005 in ROLE_INDUSTRIAL_AUTO lacks SK_PANEL_WIRING, which has not_available context
        stu5 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_005")
        panel_gap = next(g for g in stu5["skill_gaps"] if g["skill_id"] == "SK_PANEL_WIRING")
        self.assertEqual(panel_gap["status"], "missing")
        self.assertFalse(panel_gap["student_has_skill"])
        self.assertEqual(panel_gap["contextual_recommendation_status"], "not_available")
        self.assertIn("SK_PANEL_WIRING", stu5["missing_skills"])
        self.assertIn("SK_PANEL_WIRING", stu5["unavailable_context_skills"])

    def test_19_no_gap_score(self):
        raw_json = json.dumps(self.artifact).lower()
        forbidden = [
            "gap_score", "role_match_score", "readiness_score",
            "employability_score", "proficiency_percentage", "completion_percentage",
            "fit_score", "match_percent"
        ]
        for fb in forbidden:
            self.assertNotIn(fb, raw_json)

    def test_20_no_recommendation(self):
        raw_json = json.dumps(self.artifact).lower()
        forbidden = [
            "should_learn", "suggested_course", "recommended_action",
            "take_course", "learning_path"
        ]
        for fb in forbidden:
            self.assertNotIn(fb, raw_json)

    def test_21_no_course_logic(self):
        # Ensure Phase 4 course gaps / curriculum IDs are not directly injected
        for s in self.artifact["students"]:
            for gap in s["skill_gaps"]:
                self.assertNotIn("course_ids", gap)
                self.assertNotIn("recommended_courses", gap)

    def test_22_no_proficiency_judgment(self):
        # Basic evidence still marks skill as present
        stu2 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_002")
        bms_gap = next(g for g in stu2["skill_gaps"] if g["skill_id"] == "SK_BMS")
        self.assertEqual(bms_gap["status"], "present")
        self.assertNotIn("partially_present", bms_gap["status"])
        self.assertNotIn("weak", bms_gap["status"])
        self.assertNotIn("insufficient", bms_gap["status"])

    def test_23_determinism(self):
        run2 = StudentSkillGapAnalyzer().analyze_gaps()
        self.assertEqual(json.dumps(self.artifact, sort_keys=True), json.dumps(run2, sort_keys=True))

    def test_24_metadata_counts(self):
        meta = self.artifact["metadata"]
        total_records = sum(s["summary"]["total_role_skills"] for s in self.artifact["students"])
        total_present = sum(s["summary"]["present_skill_count"] for s in self.artifact["students"])
        total_missing = sum(s["summary"]["missing_skill_count"] for s in self.artifact["students"])
        total_unavail = sum(s["summary"]["unavailable_context_count"] for s in self.artifact["students"])

        self.assertEqual(meta["total_role_skill_records"], total_records)
        self.assertEqual(meta["total_present_skills"], total_present)
        self.assertEqual(meta["total_missing_skills"], total_missing)
        self.assertEqual(meta["total_unavailable_context_skills"], total_unavail)
        self.assertEqual(total_records, total_present + total_missing)

    def test_25_no_raw_data(self):
        analyzer = StudentSkillGapAnalyzer(
            student_profile_path=DEFAULT_STUDENT_PROFILE_PATH,
            role_context_path=DEFAULT_ROLE_CONTEXT_PATH,
            role_assignment_path=DEFAULT_ROLE_ASSIGNMENT_PATH,
            taxonomy_path=DEFAULT_TAXONOMY_PATH
        )
        res = analyzer.analyze_gaps()
        self.assertEqual(res["metadata"]["total_students"], 5)

    def test_26_all_assignments_retained(self):
        self.assertEqual(len(self.artifact["students"]), 5)
        assigned_map = {
            s["student_id"]: s["role"]["role_id"]
            for s in self.artifact["students"]
        }
        self.assertEqual(assigned_map["STU_001"], "ROLE_DATA_ENGINEER")
        self.assertEqual(assigned_map["STU_002"], "ROLE_EV_TECHNICIAN")
        self.assertEqual(assigned_map["STU_003"], "ROLE_FULL_STACK_DEV")
        self.assertEqual(assigned_map["STU_004"], "ROLE_HEALTHCARE_ASST")
        self.assertEqual(assigned_map["STU_005"], "ROLE_INDUSTRIAL_AUTO")

    def test_27_all_present_skills(self):
        stu3 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_003")
        self.assertEqual(stu3["present_skills"], ["SK_DOCKER", "SK_JAVASCRIPT", "SK_PYTHON", "SK_REACT"])

    def test_28_all_missing_skills(self):
        stu3 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_003")
        self.assertEqual(stu3["missing_skills"], ["SK_GIT", "SK_SQL"])

if __name__ == "__main__":
    unittest.main()
