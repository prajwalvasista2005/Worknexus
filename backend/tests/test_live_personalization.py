import unittest
from app.db.session import MockDatabaseSession
from app.db.seed import seed_all
from app.models.entities import TargetRole, RoleSkill, StudentProfile, StudentSkillEvidence
from app.services.ml_adapter import MLAdapter, HTTPException
from app.api.routes_ml import (
    get_role_context_endpoint,
    get_student_profile_endpoint,
    get_student_gap_endpoint,
    get_personalized_recommendations_endpoint,
    get_course_candidates_endpoint
)

class TestLivePersonalization(unittest.TestCase):

    def setUp(self):
        self.db = MockDatabaseSession()
        seed_all(self.db)
        self.adapter = MLAdapter()

    def test_live_role_skill_context(self):
        # 1. Valid role in live mode
        res = self.adapter.get_role_skill_context("ROLE_FULL_STACK_DEV", db=self.db, mode="live")
        self.assertEqual(res.role_id, "ROLE_FULL_STACK_DEV")
        self.assertEqual(res.role_name, "Full Stack Developer")
        self.assertFalse(res.is_synthetic_artifact)
        self.assertEqual(res.summary["target_skill_count"], 6)

        # Verify skills present
        skill_ids = [s["skill_id"] for s in res.contextual_recommendations]
        self.assertIn("SK_PYTHON", skill_ids)
        self.assertIn("SK_JAVASCRIPT", skill_ids)
        self.assertIn("SK_REACT", skill_ids)
        self.assertIn("SK_DOCKER", skill_ids)

        # 2. Unknown role raises 404
        with self.assertRaises(HTTPException) as ctx:
            self.adapter.get_role_skill_context("ROLE_NONEXISTENT", db=self.db, mode="live")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_live_student_skill_profile(self):
        # 1. Valid student string alias in live mode
        res_stu1 = self.adapter.get_student_skill_profile("STU_001", db=self.db, mode="live")
        self.assertEqual(res_stu1.student_id, "STU_001")
        self.assertFalse(res_stu1.is_synthetic_artifact)
        self.assertGreater(len(res_stu1.profile_skills), 0)

        # 2. Valid student user_id in live mode
        res_user1 = self.adapter.get_student_skill_profile("1001", db=self.db, mode="live")
        self.assertEqual(res_user1.student_id, "1001")
        self.assertFalse(res_user1.is_synthetic_artifact)
        self.assertEqual(len(res_user1.profile_skills), len(res_stu1.profile_skills))

        # 3. Unknown student raises 404
        with self.assertRaises(HTTPException) as ctx:
            self.adapter.get_student_skill_profile("STU_999", db=self.db, mode="live")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_live_student_skill_gap(self):
        # STU_003 against ROLE_FULL_STACK_DEV
        res = self.adapter.get_student_skill_gap("STU_003", "ROLE_FULL_STACK_DEV", db=self.db, mode="live")
        self.assertEqual(res.student_id, "STU_003")
        self.assertEqual(res.role["role_id"], "ROLE_FULL_STACK_DEV")
        self.assertFalse(res.is_synthetic_artifact)

        # Verify gap semantics (present + missing = total)
        total = res.summary["total_role_skills"]
        present = res.summary["present_skills_count"]
        missing = res.summary["missing_skills_count"]
        self.assertEqual(total, present + missing)
        self.assertEqual(total, 6)

        # Check statuses
        status_map = {g["skill_id"]: g["student_status"] for g in res.skill_gaps}
        self.assertIn(status_map["SK_PYTHON"], ["present", "missing"])
        self.assertIn(status_map["SK_REACT"], ["present", "missing"])

    def test_live_personalized_recommendations(self):
        # STU_003 against ROLE_FULL_STACK_DEV
        res = self.adapter.get_personalized_recommendations("STU_003", "ROLE_FULL_STACK_DEV", db=self.db, mode="live")
        self.assertEqual(res.student_id, "STU_003")
        self.assertFalse(res.is_synthetic_artifact)

        summary = res.summary
        self.assertEqual(summary["total_role_skills"], 6)
        self.assertEqual(
            summary["total_role_skills"],
            summary["already_present_count"] + summary["recommended_count"] + summary["not_recommended_count"]
        )

        for rec in res.skill_recommendations:
            self.assertIn(rec["personalized_status"], ["already_present", "recommended", "not_recommended"])
            if rec["student_status"] == "present":
                self.assertEqual(rec["personalized_status"], "already_present")

    def test_live_course_candidates(self):
        # STU_003 against ROLE_FULL_STACK_DEV
        res = self.adapter.get_course_candidates("STU_003", "ROLE_FULL_STACK_DEV", db=self.db, mode="live")
        self.assertEqual(res.student_id, "STU_003")
        self.assertFalse(res.is_synthetic_artifact)

        # Candidates must have covered_personalized_skills_count >= 1
        for cand in res.candidate_courses:
            self.assertGreaterEqual(cand["covered_personalized_skills_count"], 1)
            for sk in cand["covered_personalized_skills"]:
                self.assertIn(sk, res.personalized_skill_ids)

    def test_benchmark_mode_parity(self):
        # Benchmark mode should return synthetic artifacts (is_synthetic_artifact=True)
        r_ctx = self.adapter.get_role_skill_context("ROLE_FULL_STACK_DEV", mode="benchmark")
        self.assertTrue(r_ctx.is_synthetic_artifact)

        s_prof = self.adapter.get_student_skill_profile("STU_001", mode="benchmark")
        self.assertTrue(s_prof.is_synthetic_artifact)

        s_gap = self.adapter.get_student_skill_gap("STU_003", "ROLE_FULL_STACK_DEV", mode="benchmark")
        self.assertTrue(s_gap.is_synthetic_artifact)

        p_rec = self.adapter.get_personalized_recommendations("STU_003", "ROLE_FULL_STACK_DEV", mode="benchmark")
        self.assertTrue(p_rec.is_synthetic_artifact)

        c_cand = self.adapter.get_course_candidates("STU_003", "ROLE_FULL_STACK_DEV", mode="benchmark")
        self.assertTrue(c_cand.is_synthetic_artifact)

    def test_routes_endpoints(self):
        # Test HTTP route endpoints with live mode
        r_dict = get_role_context_endpoint(role_id="ROLE_FULL_STACK_DEV", mode="live", db=self.db, ml_adapter=self.adapter)
        self.assertEqual(r_dict["role_id"], "ROLE_FULL_STACK_DEV")
        self.assertFalse(r_dict["is_synthetic_artifact"])

        p_dict = get_student_profile_endpoint(student_id="STU_001", mode="live", db=self.db, ml_adapter=self.adapter)
        self.assertEqual(p_dict["student_id"], "STU_001")
        self.assertFalse(p_dict["is_synthetic_artifact"])

        g_dict = get_student_gap_endpoint(student_id="STU_003", role_id="ROLE_FULL_STACK_DEV", mode="live", db=self.db, ml_adapter=self.adapter)
        self.assertEqual(g_dict["student_id"], "STU_003")
        self.assertFalse(g_dict["is_synthetic_artifact"])

        rec_dict = get_personalized_recommendations_endpoint(student_id="STU_003", role_id="ROLE_FULL_STACK_DEV", mode="live", db=self.db, ml_adapter=self.adapter)
        self.assertEqual(rec_dict["student_id"], "STU_003")
        self.assertFalse(rec_dict["is_synthetic_artifact"])

        cand_dict = get_course_candidates_endpoint(student_id="STU_003", role_id="ROLE_FULL_STACK_DEV", mode="live", db=self.db, ml_adapter=self.adapter)
        self.assertEqual(cand_dict["student_id"], "STU_003")
        self.assertFalse(cand_dict["is_synthetic_artifact"])

if __name__ == '__main__':
    unittest.main()
