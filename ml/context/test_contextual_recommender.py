import unittest
import json
from pathlib import Path
from ml.context.contextual_recommender import (
    ContextAwareRecommendationEngine,
    DEFAULT_ROLE_CONTEXT_PATH,
    DEFAULT_RECOMMENDATION_PATH,
    DEFAULT_EVIDENCE_PATH,
    DEFAULT_TAXONOMY_PATH
)

class TestContextAwareRecommendationEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = ContextAwareRecommendationEngine()
        cls.artifact = cls.engine.recommend()

    def test_01_role_context_load(self):
        with open(DEFAULT_ROLE_CONTEXT_PATH, "r", encoding="utf-8") as f:
            roles = json.load(f)
        self.assertEqual(len(self.artifact["roles"]), len(roles))
        self.assertEqual(self.artifact["metadata"]["total_roles"], len(roles))
        self.assertEqual(len(self.artifact["roles"]), 5)

    def test_02_phase_6a_load(self):
        with open(DEFAULT_RECOMMENDATION_PATH, "r", encoding="utf-8") as f:
            rec_data = json.load(f)
        self.assertGreater(len(rec_data["recommendations"]), 0)
        self.assertEqual(self.artifact["metadata"]["recommendation_input"], str(DEFAULT_RECOMMENDATION_PATH.as_posix()))

    def test_03_evidence_load(self):
        with open(DEFAULT_EVIDENCE_PATH, "r", encoding="utf-8") as f:
            ev_data = json.load(f)
        self.assertGreater(len(ev_data["skills"]), 0)
        self.assertEqual(self.artifact["metadata"]["evidence_input"], str(DEFAULT_EVIDENCE_PATH.as_posix()))

    def test_04_taxonomy_validation(self):
        with open(DEFAULT_TAXONOMY_PATH, "r", encoding="utf-8") as f:
            tax = json.load(f)
        valid_ids = {s["id"] for s in tax}
        for role in self.artifact["roles"]:
            for item in role["role_skill_context"]:
                self.assertIn(item["skill_id"], valid_ids)
            for rec in role["contextual_recommendations"]:
                self.assertIn(rec["skill_id"], valid_ids)

    def test_05_role_id_uniqueness(self):
        role_ids = [r["role_id"] for r in self.artifact["roles"]]
        self.assertEqual(len(role_ids), len(set(role_ids)))

    def test_06_role_skill_uniqueness(self):
        for role in self.artifact["roles"]:
            skill_ids = [s["skill_id"] for s in role["role_skill_context"]]
            self.assertEqual(len(skill_ids), len(set(skill_ids)))
            rec_skill_ids = [s["skill_id"] for s in role["contextual_recommendations"]]
            self.assertEqual(len(rec_skill_ids), len(set(rec_skill_ids)))

    def test_07_explicit_role_mapping(self):
        with open(DEFAULT_ROLE_CONTEXT_PATH, "r", encoding="utf-8") as f:
            roles = json.load(f)
        roles_dict = {r["role_id"]: set(r["target_skill_ids"]) for r in roles}
        for role in self.artifact["roles"]:
            target_ids = roles_dict[role["role_id"]]
            for rec in role["contextual_recommendations"]:
                self.assertIn(rec["skill_id"], target_ids)
                self.assertTrue(rec["role_relevant"])

    def test_08_generic_status_preservation(self):
        with open(DEFAULT_RECOMMENDATION_PATH, "r", encoding="utf-8") as f:
            rec_data = json.load(f)
        rec_map = {r["skill_id"]: r["recommendation"]["status"] for r in rec_data["recommendations"]}
        for role in self.artifact["roles"]:
            for item in role["role_skill_context"]:
                sid = item["skill_id"]
                if sid in rec_map:
                    self.assertEqual(item["generic_recommendation_status"], rec_map[sid])

    def test_09_recommended_filter(self):
        for role in self.artifact["roles"]:
            for rec in role["contextual_recommendations"]:
                self.assertEqual(rec["generic_recommendation"]["status"], "recommended")

    def test_10_not_recommended_preservation(self):
        # E.g., SK_SPARK in ROLE_DATA_ENGINEER is not_recommended in Phase 6A
        data_eng = next(r for r in self.artifact["roles"] if r["role_id"] == "ROLE_DATA_ENGINEER")
        spark_item = next(s for s in data_eng["role_skill_context"] if s["skill_id"] == "SK_SPARK")
        self.assertEqual(spark_item["generic_recommendation_status"], "not_recommended")
        # Ensure it is NOT in contextual_recommendations
        rec_sids = [r["skill_id"] for r in data_eng["contextual_recommendations"]]
        self.assertNotIn("SK_SPARK", rec_sids)

    def test_11_evidence_preservation(self):
        with open(DEFAULT_RECOMMENDATION_PATH, "r", encoding="utf-8") as f:
            rec_data = json.load(f)
        rec_map = {r["skill_id"]: r for r in rec_data["recommendations"]}
        for role in self.artifact["roles"]:
            for rec in role["contextual_recommendations"]:
                sid = rec["skill_id"]
                expected = rec_map[sid]
                self.assertEqual(rec["evidence"], expected["evidence"])
                self.assertEqual(rec["course_context"], expected["course_context"])

    def test_12_context_reasons(self):
        for role in self.artifact["roles"]:
            for rec in role["contextual_recommendations"]:
                self.assertEqual(rec["context_reason"]["reason_id"], "explicit_role_skill_mapping")
                self.assertEqual(rec["context_reason"]["source"], "sample_role_contexts.json")

            for item in role["role_skill_context"]:
                status = item["generic_recommendation_status"]
                reason_id = item["context_reason"]["reason_id"]
                if status == "recommended":
                    self.assertEqual(reason_id, "explicit_role_skill_mapping")
                elif status == "not_recommended":
                    self.assertEqual(reason_id, "role_mapping_without_generic_recommendation")
                elif status == "not_available":
                    self.assertEqual(reason_id, "role_skill_not_in_phase6a_universe")

    def test_13_unknown_phase6a_skill(self):
        # SK_PLC in ROLE_INDUSTRIAL_AUTO is in taxonomy but not in Phase 6A (not in 5B evidence)
        auto_role = next(r for r in self.artifact["roles"] if r["role_id"] == "ROLE_INDUSTRIAL_AUTO")
        plc_item = next(s for s in auto_role["role_skill_context"] if s["skill_id"] == "SK_PLC")
        self.assertEqual(plc_item["generic_recommendation_status"], "not_available")
        self.assertEqual(plc_item["context_reason"]["reason_id"], "role_skill_not_in_phase6a_universe")
        self.assertNotIn("SK_PLC", [r["skill_id"] for r in auto_role["contextual_recommendations"]])

    def test_14_no_role_score(self):
        raw_json = json.dumps(self.artifact).lower()
        forbidden = [
            "role_score", "fit_score", "match_score", "relevance_score",
            "readiness_score", "compatibility_score", "alignment_score"
        ]
        for fb in forbidden:
            self.assertNotIn(fb, raw_json)

    def test_15_no_skill_score(self):
        raw_json = json.dumps(self.artifact).lower()
        forbidden = [
            "skill_score", "recommendation_score", "priority_score",
            "employability_score", "importance_score", "final_score"
        ]
        for fb in forbidden:
            self.assertNotIn(fb, raw_json)

    def test_16_no_ranking(self):
        role_ids = [r["role_id"] for r in self.artifact["roles"]]
        self.assertEqual(role_ids, sorted(role_ids))
        for role in self.artifact["roles"]:
            ctx_ids = [s["skill_id"] for s in role["role_skill_context"]]
            self.assertEqual(ctx_ids, sorted(ctx_ids))
            rec_ids = [s["skill_id"] for s in role["contextual_recommendations"]]
            self.assertEqual(rec_ids, sorted(rec_ids))

    def test_17_determinism(self):
        run2 = ContextAwareRecommendationEngine().recommend()
        self.assertEqual(json.dumps(self.artifact, sort_keys=True), json.dumps(run2, sort_keys=True))

    def test_18_course_isolation(self):
        raw_json = json.dumps(self.artifact).lower()
        self.assertNotIn("recommend_course", raw_json)
        self.assertNotIn("best_course", raw_json)
        self.assertNotIn("learning_path", raw_json)

    def test_19_raw_data_isolation(self):
        engine = ContextAwareRecommendationEngine(
            role_context_path=DEFAULT_ROLE_CONTEXT_PATH,
            recommendation_path=DEFAULT_RECOMMENDATION_PATH,
            evidence_path=DEFAULT_EVIDENCE_PATH,
            taxonomy_path=DEFAULT_TAXONOMY_PATH
        )
        res = engine.recommend()
        self.assertEqual(res["metadata"]["total_roles"], 5)

    def test_20_count_consistency(self):
        total_mappings = 0
        total_rec = 0
        for role in self.artifact["roles"]:
            t_cnt = role["target_skill_count"]
            r_cnt = role["recommended_target_skill_count"]
            nr_cnt = role["not_recommended_target_skill_count"]
            u_cnt = role["unavailable_target_skill_count"]
            self.assertEqual(t_cnt, r_cnt + nr_cnt + u_cnt)
            self.assertEqual(t_cnt, len(role["role_skill_context"]))
            self.assertEqual(r_cnt, len(role["contextual_recommendations"]))
            total_mappings += t_cnt
            total_rec += r_cnt

        self.assertEqual(self.artifact["metadata"]["total_role_skill_mappings"], total_mappings)
        self.assertEqual(self.artifact["metadata"]["total_contextual_recommendations"], total_rec)
        self.assertEqual(self.artifact["metadata"]["total_role_skill_context_records"], total_mappings)

    def test_21_all_roles_retained(self):
        self.assertEqual(len(self.artifact["roles"]), 5)
        role_ids = {r["role_id"] for r in self.artifact["roles"]}
        expected_roles = {
            "ROLE_DATA_ENGINEER",
            "ROLE_EV_TECHNICIAN",
            "ROLE_FULL_STACK_DEV",
            "ROLE_HEALTHCARE_ASST",
            "ROLE_INDUSTRIAL_AUTO"
        }
        self.assertEqual(role_ids, expected_roles)

    def test_22_all_role_skills_retained_in_context(self):
        with open(DEFAULT_ROLE_CONTEXT_PATH, "r", encoding="utf-8") as f:
            roles = json.load(f)
        for role in roles:
            art_role = next(r for r in self.artifact["roles"] if r["role_id"] == role["role_id"])
            art_sids = {s["skill_id"] for s in art_role["role_skill_context"]}
            self.assertEqual(art_sids, set(role["target_skill_ids"]))

    def test_23_no_llm_references(self):
        raw_json = json.dumps(self.artifact).lower()
        forbidden = ["gpt", "openai", "claude", "llama", "embedding", "vector", "temperature", "prompt"]
        for fb in forbidden:
            self.assertNotIn(fb, raw_json)

    def test_24_source_traceability(self):
        for role in self.artifact["roles"]:
            for item in role["role_skill_context"]:
                self.assertEqual(item["context_reason"]["source"], "sample_role_contexts.json")

if __name__ == "__main__":
    unittest.main()
