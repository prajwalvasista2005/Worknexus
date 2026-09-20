import unittest
import json
from pathlib import Path
from ml.student.student_profile import (
    StudentProfileEngine,
    DEFAULT_STUDENT_PROFILE_PATH,
    DEFAULT_TAXONOMY_PATH,
    ALLOWED_EVIDENCE_TYPES,
    ALLOWED_EVIDENCE_STRENGTHS
)

class TestStudentProfileEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = StudentProfileEngine()
        cls.artifact = cls.engine.process_profiles()

    def test_01_input_load(self):
        with open(DEFAULT_STUDENT_PROFILE_PATH, "r", encoding="utf-8") as f:
            students = json.load(f)
        self.assertEqual(len(self.artifact["students"]), len(students))
        self.assertEqual(self.artifact["metadata"]["total_students"], len(students))
        self.assertEqual(len(self.artifact["students"]), 5)

    def test_02_taxonomy_load(self):
        with open(DEFAULT_TAXONOMY_PATH, "r", encoding="utf-8") as f:
            tax = json.load(f)
        self.assertGreater(len(tax), 0)
        self.assertEqual(self.artifact["metadata"]["taxonomy_version"], "1")

    def test_03_student_id_uniqueness(self):
        student_ids = [s["student_id"] for s in self.artifact["students"]]
        self.assertEqual(len(student_ids), len(set(student_ids)))

    def test_04_student_id_validation(self):
        # Test error handling when student_id is empty
        invalid_data = [
            {"student_id": "", "profile_name": "Invalid", "skills": []}
        ]
        test_path = DEFAULT_STUDENT_PROFILE_PATH.parent / "_test_invalid_stu.json"
        with open(test_path, "w", encoding="utf-8") as f:
            json.dump(invalid_data, f)
        try:
            eng = StudentProfileEngine(student_profile_path=test_path)
            res = eng.process_profiles()
            self.assertEqual(len(res["students"]), 0)
            self.assertGreater(len(res["errors"]), 0)
        finally:
            if test_path.exists():
                test_path.unlink()

    def test_05_profile_name_validation(self):
        invalid_data = [
            {"student_id": "STU_TEST", "profile_name": "   ", "skills": []}
        ]
        test_path = DEFAULT_STUDENT_PROFILE_PATH.parent / "_test_invalid_name.json"
        with open(test_path, "w", encoding="utf-8") as f:
            json.dump(invalid_data, f)
        try:
            eng = StudentProfileEngine(student_profile_path=test_path)
            res = eng.process_profiles()
            self.assertEqual(len(res["students"]), 0)
            self.assertGreater(len(res["errors"]), 0)
        finally:
            if test_path.exists():
                test_path.unlink()

    def test_06_skill_id_validation(self):
        with open(DEFAULT_TAXONOMY_PATH, "r", encoding="utf-8") as f:
            tax = json.load(f)
        valid_ids = {s["id"] for s in tax}
        for s in self.artifact["students"]:
            for sk in s["skills"]:
                self.assertIn(sk["skill_id"], valid_ids)

    def test_07_duplicate_skills(self):
        invalid_data = [
            {
                "student_id": "STU_TEST",
                "profile_name": "Dup Skills Student",
                "skills": [
                    {"skill_id": "SK_PYTHON", "evidence_type": "project", "evidence_strength": "basic"},
                    {"skill_id": "SK_PYTHON", "evidence_type": "course_completed", "evidence_strength": "intermediate"}
                ]
            }
        ]
        test_path = DEFAULT_STUDENT_PROFILE_PATH.parent / "_test_dup_skills.json"
        with open(test_path, "w", encoding="utf-8") as f:
            json.dump(invalid_data, f)
        try:
            eng = StudentProfileEngine(student_profile_path=test_path)
            res = eng.process_profiles()
            # Only first instance retained or error recorded
            self.assertGreater(len(res["errors"]), 0)
            self.assertTrue(any("Duplicate skill_id" in err.get("error", "") for err in res["errors"]))
        finally:
            if test_path.exists():
                test_path.unlink()

    def test_08_evidence_type(self):
        for s in self.artifact["students"]:
            for sk in s["skills"]:
                for ev in sk["evidence"]:
                    self.assertIn(ev["evidence_type"], ALLOWED_EVIDENCE_TYPES)

    def test_09_evidence_strength(self):
        for s in self.artifact["students"]:
            for sk in s["skills"]:
                for ev in sk["evidence"]:
                    self.assertIn(ev["evidence_strength"], ALLOWED_EVIDENCE_STRENGTHS)

    def test_10_empty_evidence(self):
        invalid_data = [
            {
                "student_id": "STU_TEST",
                "profile_name": "Empty Ev",
                "skills": [
                    {"skill_id": "SK_PYTHON", "evidence": []}
                ]
            }
        ]
        test_path = DEFAULT_STUDENT_PROFILE_PATH.parent / "_test_empty_ev.json"
        with open(test_path, "w", encoding="utf-8") as f:
            json.dump(invalid_data, f)
        try:
            eng = StudentProfileEngine(student_profile_path=test_path)
            res = eng.process_profiles()
            self.assertGreater(len(res["errors"]), 0)
            self.assertTrue(any("Evidence list must be a non-empty" in err.get("error", "") for err in res["errors"]))
        finally:
            if test_path.exists():
                test_path.unlink()

    def test_11_multiple_evidence(self):
        stu1 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_001")
        py_skill = next(sk for sk in stu1["skills"] if sk["skill_id"] == "SK_PYTHON")
        self.assertEqual(len(py_skill["evidence"]), 2)
        ev_types = {ev["evidence_type"] for ev in py_skill["evidence"]}
        self.assertEqual(ev_types, {"project", "certification"})

    def test_12_taxonomy_name_resolution(self):
        with open(DEFAULT_TAXONOMY_PATH, "r", encoding="utf-8") as f:
            tax = json.load(f)
        tax_names = {s["id"]: s["name"] for s in tax}
        for s in self.artifact["students"]:
            for sk in s["skills"]:
                self.assertEqual(sk["skill_name"], tax_names[sk["skill_id"]])

    def test_13_category_resolution(self):
        with open(DEFAULT_TAXONOMY_PATH, "r", encoding="utf-8") as f:
            tax = json.load(f)
        tax_cats = {s["id"]: s["category"] for s in tax}
        for s in self.artifact["students"]:
            for sk in s["skills"]:
                self.assertEqual(sk["category"], tax_cats[sk["skill_id"]])

    def test_14_category_derivation(self):
        for s in self.artifact["students"]:
            expected_cats = sorted(list({sk["category"] for sk in s["skills"]}))
            self.assertEqual(s["categories_present"], expected_cats)

    def test_15_skill_count(self):
        for s in self.artifact["students"]:
            self.assertEqual(s["skill_count"], len(s["skills"]))

    def test_16_no_target_role(self):
        raw_json = json.dumps(self.artifact).lower()
        forbidden = ["target_role", "desired_job", "career_goal", "target_role_id", "role_id"]
        for fb in forbidden:
            self.assertNotIn(fb, raw_json)

    def test_17_no_recommendations(self):
        raw_json = json.dumps(self.artifact).lower()
        forbidden = ["recommendation", "recommended_skills", "suggested_skills", "learning_path"]
        for fb in forbidden:
            self.assertNotIn(fb, raw_json)

    def test_18_no_proficiency_score(self):
        raw_json = json.dumps(self.artifact).lower()
        forbidden = [
            "proficiency_score", "skill_score", "confidence_score",
            "expertise_score", "overall_strength", "mastery_score"
        ]
        for fb in forbidden:
            self.assertNotIn(fb, raw_json)

    def test_19_determinism(self):
        run2 = StudentProfileEngine().process_profiles()
        self.assertEqual(json.dumps(self.artifact, sort_keys=True), json.dumps(run2, sort_keys=True))

    def test_20_no_raw_data(self):
        engine = StudentProfileEngine(
            student_profile_path=DEFAULT_STUDENT_PROFILE_PATH,
            taxonomy_path=DEFAULT_TAXONOMY_PATH
        )
        res = engine.process_profiles()
        self.assertEqual(res["metadata"]["total_students"], 5)

    def test_21_all_students_retained(self):
        with open(DEFAULT_STUDENT_PROFILE_PATH, "r", encoding="utf-8") as f:
            raw_students = json.load(f)
        raw_ids = [s["student_id"] for s in raw_students]
        art_ids = [s["student_id"] for s in self.artifact["students"]]
        self.assertEqual(sorted(raw_ids), sorted(art_ids))

    def test_22_all_evidence_retained(self):
        stu5 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_005")
        can_skill = next(sk for sk in stu5["skills"] if sk["skill_id"] == "SK_CAN")
        self.assertEqual(len(can_skill["evidence"]), 2)
        self.assertEqual(can_skill["evidence"][0]["evidence_type"], "assessment")
        self.assertEqual(can_skill["evidence"][0]["evidence_strength"], "intermediate")
        self.assertEqual(can_skill["evidence"][1]["evidence_type"], "project")
        self.assertEqual(can_skill["evidence"][1]["evidence_strength"], "advanced")

    def test_23_metadata_counts(self):
        total_skills = sum(s["skill_count"] for s in self.artifact["students"])
        all_unique = set()
        cat_counts = {}
        for s in self.artifact["students"]:
            for sk in s["skills"]:
                all_unique.add(sk["skill_id"])
                c = sk["category"]
                cat_counts[c] = cat_counts.get(c, 0) + 1

        self.assertEqual(self.artifact["metadata"]["total_skill_records"], total_skills)
        self.assertEqual(self.artifact["metadata"]["total_unique_skills"], len(all_unique))
        self.assertEqual(self.artifact["metadata"]["category_counts"], dict(sorted(cat_counts.items())))

    def test_24_sorting(self):
        student_ids = [s["student_id"] for s in self.artifact["students"]]
        self.assertEqual(student_ids, sorted(student_ids))
        for s in self.artifact["students"]:
            skill_ids = [sk["skill_id"] for sk in s["skills"]]
            self.assertEqual(skill_ids, sorted(skill_ids))
            self.assertEqual(s["categories_present"], sorted(s["categories_present"]))
            for sk in s["skills"]:
                ev_tuples = [(ev["evidence_type"], ev["evidence_strength"]) for ev in sk["evidence"]]
                self.assertEqual(ev_tuples, sorted(ev_tuples))

if __name__ == "__main__":
    unittest.main()
