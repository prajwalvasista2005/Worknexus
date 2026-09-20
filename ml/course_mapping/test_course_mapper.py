import unittest
import json
from pathlib import Path
from ml.course_mapping.course_mapper import (
    PersonalizedCourseMapper,
    DEFAULT_RECOMMENDATION_PATH,
    DEFAULT_COURSE_PATH,
    DEFAULT_TAXONOMY_PATH
)

class TestPersonalizedCourseMapper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mapper = PersonalizedCourseMapper()
        cls.artifact = cls.mapper.map_courses()

    def test_01_personalized_input(self):
        with open(DEFAULT_RECOMMENDATION_PATH, "r", encoding="utf-8") as f:
            recs = json.load(f)
        self.assertEqual(len(self.artifact["students"]), len(recs["students"]))

    def test_02_course_input(self):
        with open(DEFAULT_COURSE_PATH, "r", encoding="utf-8") as f:
            courses = json.load(f)
        self.assertEqual(len(courses), 5)

    def test_03_taxonomy_input(self):
        with open(DEFAULT_TAXONOMY_PATH, "r", encoding="utf-8") as f:
            tax = json.load(f)
        self.assertEqual(len(tax), 68)

    def test_04_student_count(self):
        self.assertEqual(self.artifact["metadata"]["total_students"], 5)
        self.assertEqual(len(self.artifact["students"]), 5)

    def test_05_personalized_skill_count(self):
        with open(DEFAULT_RECOMMENDATION_PATH, "r", encoding="utf-8") as f:
            recs = json.load(f)
        expected_total = recs["metadata"]["total_personalized_recommendations"]
        self.assertEqual(self.artifact["metadata"]["total_personalized_skills"], expected_total)
        self.assertEqual(self.artifact["metadata"]["total_personalized_skills"], 8)

    def test_06_only_recommended_skills_mapped(self):
        # Already present skills like SK_PYTHON, SK_DOCKER must NOT be in student's skill_course_mapping
        stu1 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_001")
        mapped_sids = {m["skill_id"] for m in stu1["skill_course_mapping"]}
        self.assertNotIn("SK_PYTHON", mapped_sids)
        self.assertNotIn("SK_SQL", mapped_sids)

    def test_07_not_recommended_exclusion(self):
        # Not recommended skills like SK_SPARK in STU_001 or SK_GIT in STU_003 must NOT be in skill_course_mapping
        stu1 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_001")
        mapped_sids1 = {m["skill_id"] for m in stu1["skill_course_mapping"]}
        self.assertNotIn("SK_SPARK", mapped_sids1)

        stu3 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_003")
        mapped_sids3 = {m["skill_id"] for m in stu3["skill_course_mapping"]}
        self.assertNotIn("SK_GIT", mapped_sids3)

    def test_08_explicit_course_matching(self):
        with open(DEFAULT_COURSE_PATH, "r", encoding="utf-8") as f:
            courses = json.load(f)
        course_skills_map = {c["course_id"]: set(c.get("skill_ids", [])) for c in courses}

        for s in self.artifact["students"]:
            for m in s["skill_course_mapping"]:
                sid = m["skill_id"]
                for c in m["matching_courses"]:
                    cid = c["course_id"]
                    self.assertIn(sid, course_skills_map[cid])

    def test_09_multiple_course_match(self):
        # SK_SQL in STU_003 exists in Course 101 and Course 102
        stu3 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_003")
        sql_map = next(m for m in stu3["skill_course_mapping"] if m["skill_id"] == "SK_SQL")
        self.assertEqual(sql_map["coverage_status"], "covered")
        self.assertEqual(len(sql_map["matching_courses"]), 2)
        c_ids = [c["course_id"] for c in sql_map["matching_courses"]]
        self.assertEqual(c_ids, [101, 102])

    def test_10_zero_course_match(self):
        # SK_AWS in STU_001 has no matching courses
        stu1 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_001")
        aws_map = next(m for m in stu1["skill_course_mapping"] if m["skill_id"] == "SK_AWS")
        self.assertEqual(aws_map["coverage_status"], "not_covered")
        self.assertEqual(aws_map["matching_courses"], [])

        # SK_CAN in STU_002 has no matching courses (missing from Course 42)
        stu2 = next(s for s in self.artifact["students"] if s["student_id"] == "STU_002")
        can_map = next(m for m in stu2["skill_course_mapping"] if m["skill_id"] == "SK_CAN")
        self.assertEqual(can_map["coverage_status"], "not_covered")
        self.assertEqual(can_map["matching_courses"], [])

    def test_11_no_fuzzy_matching(self):
        # Ensure only exact canonical skill IDs matched
        for s in self.artifact["students"]:
            for m in s["skill_course_mapping"]:
                self.assertTrue(m["skill_id"].startswith("SK_"))

    def test_12_taxonomy_validation(self):
        with open(DEFAULT_TAXONOMY_PATH, "r", encoding="utf-8") as f:
            tax = json.load(f)
        valid_ids = {s["id"] for s in tax}
        for s in self.artifact["students"]:
            for m in s["skill_course_mapping"]:
                self.assertIn(m["skill_id"], valid_ids)

    def test_13_course_validation(self):
        with open(DEFAULT_COURSE_PATH, "r", encoding="utf-8") as f:
            courses = json.load(f)
        valid_cids = {c["course_id"] for c in courses}
        for s in self.artifact["students"]:
            for m in s["skill_course_mapping"]:
                for c in m["matching_courses"]:
                    self.assertIn(c["course_id"], valid_cids)

    def test_14_course_duplicate_prevention(self):
        for s in self.artifact["students"]:
            for m in s["skill_course_mapping"]:
                cids = [c["course_id"] for c in m["matching_courses"]]
                self.assertEqual(len(cids), len(set(cids)))

    def test_15_student_count_consistency(self):
        with open(DEFAULT_RECOMMENDATION_PATH, "r", encoding="utf-8") as f:
            recs = json.load(f)
        r_ids = [s["student_id"] for s in recs["students"]]
        m_ids = [s["student_id"] for s in self.artifact["students"]]
        self.assertEqual(r_ids, m_ids)

    def test_16_role_preservation(self):
        with open(DEFAULT_RECOMMENDATION_PATH, "r", encoding="utf-8") as f:
            recs = json.load(f)
        r_roles = {s["student_id"]: s["role"] for s in recs["students"]}
        for s in self.artifact["students"]:
            sid = s["student_id"]
            self.assertEqual(s["role"], r_roles[sid])

    def test_17_skill_name_preservation(self):
        with open(DEFAULT_TAXONOMY_PATH, "r", encoding="utf-8") as f:
            tax = json.load(f)
        names_map = {s["id"]: s["name"] for s in tax}
        for s in self.artifact["students"]:
            for m in s["skill_course_mapping"]:
                self.assertEqual(m["skill_name"], names_map[m["skill_id"]])

    def test_18_course_name_preservation(self):
        with open(DEFAULT_COURSE_PATH, "r", encoding="utf-8") as f:
            courses = json.load(f)
        cname_map = {c["course_id"]: c["name"] for c in courses}
        for s in self.artifact["students"]:
            for m in s["skill_course_mapping"]:
                for c in m["matching_courses"]:
                    self.assertEqual(c["course_name"], cname_map[c["course_id"]])

    def test_19_coverage_status(self):
        for s in self.artifact["students"]:
            for m in s["skill_course_mapping"]:
                if len(m["matching_courses"]) > 0:
                    self.assertEqual(m["coverage_status"], "covered")
                else:
                    self.assertEqual(m["coverage_status"], "not_covered")

    def test_20_summary_count(self):
        for s in self.artifact["students"]:
            summary = s["summary"]
            tot = summary["total_personalized_skills"]
            cov = summary["covered_personalized_skills"]
            not_cov = summary["not_covered_personalized_skills"]
            self.assertEqual(tot, cov + not_cov)
            self.assertEqual(tot, len(s["skill_course_mapping"]))

    def test_21_global_mapping(self):
        with open(DEFAULT_TAXONOMY_PATH, "r", encoding="utf-8") as f:
            tax = json.load(f)
        self.assertEqual(len(self.artifact["global_skill_course_mapping"]), len(tax))
        g_sids = [g["skill_id"] for g in self.artifact["global_skill_course_mapping"]]
        self.assertEqual(g_sids, sorted(g_sids))

    def test_22_no_course_ranking(self):
        raw_json = json.dumps(self.artifact).lower()
        forbidden = [
            "best_course", "top_course", "course_rank", "course_score",
            "course_priority", "course_fit_score", "course_quality_score",
            "course_relevance_score"
        ]
        for fb in forbidden:
            self.assertNotIn(fb, raw_json)

    def test_23_no_learning_path(self):
        raw_json = json.dumps(self.artifact).lower()
        forbidden = ["learning_path", "prerequisite", "training_plan", "course_sequence"]
        for fb in forbidden:
            self.assertNotIn(fb, raw_json)

    def test_24_no_new_recommendation(self):
        with open(DEFAULT_RECOMMENDATION_PATH, "r", encoding="utf-8") as f:
            recs = json.load(f)
        for r_stu in recs["students"]:
            sid = r_stu["student_id"]
            m_stu = next(s for s in self.artifact["students"] if s["student_id"] == sid)
            r_rec_sids = set(r_stu["recommended_skills"])
            m_rec_sids = {m["skill_id"] for m in m_stu["skill_course_mapping"]}
            self.assertEqual(r_rec_sids, m_rec_sids)

    def test_25_no_raw_data(self):
        mapper = PersonalizedCourseMapper(
            recommendation_path=DEFAULT_RECOMMENDATION_PATH,
            course_path=DEFAULT_COURSE_PATH,
            taxonomy_path=DEFAULT_TAXONOMY_PATH
        )
        res = mapper.map_courses()
        self.assertEqual(res["metadata"]["total_students"], 5)

    def test_26_determinism(self):
        run2 = PersonalizedCourseMapper().map_courses()
        self.assertEqual(json.dumps(self.artifact, sort_keys=True), json.dumps(run2, sort_keys=True))

    def test_27_sorting(self):
        # Students sorted by student_id ASC
        stu_ids = [s["student_id"] for s in self.artifact["students"]]
        self.assertEqual(stu_ids, sorted(stu_ids))
        for s in self.artifact["students"]:
            sids = [m["skill_id"] for m in s["skill_course_mapping"]]
            self.assertEqual(sids, sorted(sids))
            for m in s["skill_course_mapping"]:
                cids = [c["course_id"] for c in m["matching_courses"]]
                self.assertEqual(cids, sorted(cids))

    def test_28_error_visibility(self):
        self.assertIn("errors", self.artifact)
        self.assertEqual(len(self.artifact["errors"]), 0)

    def test_29_course_immutability(self):
        with open(DEFAULT_COURSE_PATH, "r", encoding="utf-8") as f:
            courses = json.load(f)
        self.assertEqual(len(courses), 5)
        ev_course = next(c for c in courses if c["course_id"] == 42)
        self.assertNotIn("SK_CAN", ev_course["skill_ids"])

    def test_30_taxonomy_immutability(self):
        with open(DEFAULT_TAXONOMY_PATH, "r", encoding="utf-8") as f:
            tax = json.load(f)
        self.assertEqual(len(tax), 68)

if __name__ == "__main__":
    unittest.main()
