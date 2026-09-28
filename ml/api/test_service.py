import unittest
import json
import inspect
from pathlib import Path
from ml.api.service import (
    MLService,
    PATH_DEMAND,
    PATH_COURSE_GAP,
    PATH_EMPLOYER_FEEDBACK,
    PATH_EVIDENCE,
    PATH_GENERIC_REC,
    PATH_CONTEXT_REC,
    PATH_STUDENT_PROFILE,
    PATH_STUDENT_GAP,
    PATH_PERSONALIZED_REC,
    PATH_COURSE_SELECTION
)
from ml.api.models import (
    MLError,
    InvalidInputError,
    ArtifactNotFoundError,
    SchemaValidationError,
    UnknownSkillError,
    UnknownStudentError,
    UnknownRoleError,
    JobProcessingResult,
    SkillDemandResult,
    CourseGapResult,
    EmployerFeedbackResult,
    SkillEvidenceResult,
    SkillRecommendationResult,
    RoleSkillContextResult,
    StudentProfileResult,
    StudentGapResult,
    PersonalizedRecommendationResult,
    CourseCandidateResult
)

class TestMLService(unittest.TestCase):

    def setUp(self):
        self.service = MLService()

    def test_01_import_ml_service(self):
        """TEST 01: MLService imports and initializes cleanly."""
        self.assertIsInstance(self.service, MLService)
        self.assertEqual(len(self.service.valid_skill_ids), 68)

    def test_02_no_fastapi_dependency(self):
        """TEST 02: Verify no FastAPI dependencies in ml/api package."""
        import ml.api.service as s_mod
        import ml.api.models as m_mod
        for mod in [s_mod, m_mod]:
            source = inspect.getsource(mod)
            for term in ["fastapi", "APIRouter", "FastAPI", "Request", "Response", "uvicorn"]:
                self.assertNotIn(term, source)

    def test_03_no_database_dependency(self):
        """TEST 03: Verify no database/ORM dependencies in ml/api package."""
        import ml.api.service as s_mod
        import ml.api.models as m_mod
        for mod in [s_mod, m_mod]:
            source = inspect.getsource(mod)
            for term in ["sqlalchemy", "psycopg", "pymysql", "sqlite3", "alembic", "sessionmaker"]:
                self.assertNotIn(term, source)

    def test_04_no_http_dependency(self):
        """TEST 04: Verify no HTTP client dependencies in ml/api package."""
        import ml.api.service as s_mod
        import ml.api.models as m_mod
        for mod in [s_mod, m_mod]:
            source = inspect.getsource(mod)
            for term in ["requests", "httpx", "urllib.request", "aiohttp"]:
                self.assertNotIn(term, source)

    def test_05_frozen_extract_skills_contract(self):
        """TEST 05: Frozen extract_skills contract returns expected structure."""
        text = "Proficient in Python, SQL, and Docker containerization."
        res = self.service.extract_skills(text)
        self.assertIsInstance(res, list)
        self.assertGreaterEqual(len(res), 3)
        for item in res:
            self.assertIsInstance(item, dict)
            self.assertEqual(set(item.keys()), {"skill_id", "confidence_score"})

    def test_06_extraction_output_exact_keys(self):
        """TEST 06: Extraction output contains exactly skill_id and confidence_score."""
        res = self.service.extract_skills("Experienced in React and FastApi.")
        for r in res:
            self.assertEqual(list(r.keys()), ["skill_id", "confidence_score"])
            self.assertIsInstance(r["skill_id"], str)
            self.assertIsInstance(r["confidence_score"], float)

    def test_07_invalid_extraction_text_type(self):
        """TEST 07: Invalid extraction text type raises InvalidInputError."""
        with self.assertRaises(InvalidInputError):
            self.service.extract_skills(None)
        with self.assertRaises(InvalidInputError):
            self.service.extract_skills(12345)
        with self.assertRaises(InvalidInputError):
            self.service.extract_skills(["Python", "SQL"])

    def test_08_process_job_delegation(self):
        """TEST 08: process_job extracts skills and returns JobProcessingResult."""
        job_data = {
            "id": "JOB_001",
            "title": "Senior Data Engineer",
            "company": "Tech Corp",
            "location": "Bengaluru",
            "description": "Must have expertise in Apache Airflow, Python, and SQL databases."
        }
        res = self.service.process_job(job_data)
        self.assertIsInstance(res, JobProcessingResult)
        self.assertEqual(res.job_id, "JOB_001")
        self.assertEqual(res.company, "Tech Corp")
        extracted_ids = {s["skill_id"] for s in res.extracted_skills}
        self.assertIn("SK_AIRFLOW", extracted_ids)
        self.assertIn("SK_PYTHON", extracted_ids)
        self.assertIn("SK_SQL", extracted_ids)

    def test_09_demand_artifact_loading(self):
        """TEST 09: Demand artifact loads correctly via get_skill_demand."""
        res = self.service.get_skill_demand()
        self.assertIsInstance(res, SkillDemandResult)
        self.assertEqual(res.total_jobs_analyzed, 295)
        self.assertEqual(res.total_unique_skills_demanded, 30)
        self.assertTrue(res.is_synthetic_artifact)

    def test_10_course_gap_artifact_loading(self):
        """TEST 10: Course gap artifact loads correctly via get_course_skill_gaps."""
        res = self.service.get_course_skill_gaps()
        self.assertIsInstance(res, CourseGapResult)
        self.assertEqual(res.total_courses_analyzed, 5)
        self.assertEqual(res.total_skills_demanded, 30)
        self.assertTrue(res.is_synthetic_artifact)

    def test_11_employer_feedback_runtime_analysis(self):
        """TEST 11: Employer feedback runtime analysis works via analyze_employer_feedback."""
        sample_fb = [
            {
                "feedback_id": "FB_TEST_1",
                "employer_id": "EMP_001",
                "course_id": 42,
                "rating": 4,
                "comments": "Great diagnostics and CAN Bus troubleshooting skills.",
                "timestamp": "2026-09-01T10:00:00Z"
            }
        ]
        res = self.service.analyze_employer_feedback(sample_fb)
        self.assertIsInstance(res, EmployerFeedbackResult)
        self.assertEqual(res.total_feedback_records, 1)
        detected_ids = {s["skill_id"] for s in res.detected_skills}
        self.assertIn("SK_CAN", detected_ids)

    def test_12_employer_feedback_comment_only_extraction(self):
        """TEST 12: Employer feedback extracts from comment text only."""
        sample_fb = {
            "feedback_id": "FB_TEST_2",
            "employer_id": "Python Software Inc",  # Employer name has Python, but comment has only Docker
            "course_id": 101,
            "rating": 5,
            "comments": "Needs better Docker skills.",
            "timestamp": "2026-09-01T10:00:00Z"
        }
        res = self.service.analyze_employer_feedback(sample_fb)
        detected_ids = {s["skill_id"] for s in res.detected_skills}
        self.assertIn("SK_DOCKER", detected_ids)
        self.assertNotIn("SK_PYTHON", detected_ids)

    def test_13_evidence_artifact_loading(self):
        """TEST 13: Evidence artifact loads correctly via get_skill_evidence."""
        res = self.service.get_skill_evidence()
        self.assertIsInstance(res, SkillEvidenceResult)
        self.assertEqual(res.total_skills_evaluated, 35)
        self.assertTrue(res.is_synthetic_artifact)

    def test_14_generic_recommendation_artifact_loading(self):
        """TEST 14: Generic recommendation artifact loads correctly via get_skill_recommendations."""
        res = self.service.get_skill_recommendations()
        self.assertIsInstance(res, SkillRecommendationResult)
        self.assertEqual(res.total_skills_evaluated, 35)
        self.assertEqual(len(res.recommended_skills), 30)
        self.assertEqual(len(res.not_recommended_skills), 5)

    def test_15_role_context_artifact_loading(self):
        """TEST 15: Role context artifact loads correctly via get_role_skill_context."""
        res = self.service.get_role_skill_context("ROLE_DATA_ENGINEER")
        self.assertIsInstance(res, RoleSkillContextResult)
        self.assertEqual(res.role_id, "ROLE_DATA_ENGINEER")
        self.assertEqual(res.role_name, "Data Engineer")
        self.assertGreaterEqual(len(res.contextual_recommendations), 4)

    def test_16_student_profile_artifact_loading(self):
        """TEST 16: Student profile artifact loads correctly via get_student_skill_profile."""
        res = self.service.get_student_skill_profile("STU_001")
        self.assertIsInstance(res, StudentProfileResult)
        self.assertEqual(res.student_id, "STU_001")
        self.assertGreaterEqual(len(res.profile_skills), 2)

    def test_17_student_gap_lookup(self):
        """TEST 17: Student gap lookup works via get_student_skill_gap."""
        res = self.service.get_student_skill_gap("STU_001", "ROLE_DATA_ENGINEER")
        self.assertIsInstance(res, StudentGapResult)
        self.assertEqual(res.student_id, "STU_001")
        self.assertEqual(res.role["role_id"], "ROLE_DATA_ENGINEER")
        self.assertEqual(res.summary["missing_skill_count"], 3)

    def test_18_unknown_student_error(self):
        """TEST 18: Unknown student ID raises UnknownStudentError."""
        with self.assertRaises(UnknownStudentError):
            self.service.get_student_skill_profile("STU_NONEXISTENT")
        with self.assertRaises(UnknownStudentError):
            self.service.get_student_skill_gap("STU_NONEXISTENT", "ROLE_DATA_ENGINEER")
        with self.assertRaises(UnknownStudentError):
            self.service.get_personalized_recommendations("STU_NONEXISTENT", "ROLE_DATA_ENGINEER")
        with self.assertRaises(UnknownStudentError):
            self.service.get_course_candidates("STU_NONEXISTENT", "ROLE_DATA_ENGINEER")

    def test_19_unknown_role_error(self):
        """TEST 19: Unknown role ID raises UnknownRoleError."""
        with self.assertRaises(UnknownRoleError):
            self.service.get_role_skill_context("ROLE_INVALID")
        with self.assertRaises(UnknownRoleError):
            self.service.get_student_skill_gap("STU_001", "ROLE_INVALID")
        with self.assertRaises(UnknownRoleError):
            self.service.get_personalized_recommendations("STU_001", "ROLE_INVALID")
        with self.assertRaises(UnknownRoleError):
            self.service.get_course_candidates("STU_001", "ROLE_INVALID")

    def test_20_personalized_recommendations_lookup(self):
        """TEST 20: Personalized recommendations lookup works via get_personalized_recommendations."""
        res = self.service.get_personalized_recommendations("STU_001", "ROLE_DATA_ENGINEER")
        self.assertIsInstance(res, PersonalizedRecommendationResult)
        self.assertEqual(res.student_id, "STU_001")
        self.assertEqual(res.summary["recommended_skill_count"], 2)

    def test_21_course_candidates_lookup(self):
        """TEST 21: Course candidate lookup works via get_course_candidates."""
        res = self.service.get_course_candidates("STU_001", "ROLE_DATA_ENGINEER")
        self.assertIsInstance(res, CourseCandidateResult)
        self.assertEqual(res.student_id, "STU_001")
        self.assertEqual(len(res.candidate_courses), 1)
        self.assertEqual(res.candidate_courses[0]["course_id"], 102)
        self.assertEqual(res.uncovered_personalized_skills, ["SK_AWS"])

    def test_22_unknown_skill_id_rejection(self):
        """TEST 22: Unknown skill IDs are not in valid_skill_ids."""
        self.assertNotIn("SK_NONEXISTENT_XYZ", self.service.valid_skill_ids)

    def test_23_invalid_artifact_path_handling(self):
        """TEST 23: Missing artifact path raises ArtifactNotFoundError."""
        with self.assertRaises(ArtifactNotFoundError):
            self.service._load_artifact(Path("C:/nonexistent/path/artifact.json"))

    def test_24_no_recommendation_logic_duplicated(self):
        """TEST 24: service.py delegates rather than re-implementing recommendation algorithms."""
        source = inspect.getsource(self.service.get_personalized_recommendations)
        self.assertIn("PATH_PERSONALIZED_REC", source)

    def test_25_7c_output_consistency(self):
        """TEST 25: 7C output remains consistent via get_personalized_recommendations."""
        res_stu3 = self.service.get_personalized_recommendations("STU_003", "ROLE_FULL_STACK_DEV")
        rec_ids = [
            r["skill_id"] for r in res_stu3.skill_recommendations
            if r.get("personalized_status") == "recommended"
        ]
        self.assertEqual(rec_ids, ["SK_SQL"])

    def test_26_7e_output_consistency(self):
        """TEST 26: 7E output remains consistent via get_course_candidates."""
        res_stu2 = self.service.get_course_candidates("STU_002", "ROLE_EV_TECHNICIAN")
        self.assertEqual(len(res_stu2.candidate_courses), 1)
        self.assertEqual(res_stu2.candidate_courses[0]["course_id"], 42)
        self.assertEqual(res_stu2.candidate_courses[0]["covered_personalized_skill_ids"], ["SK_DIAG", "SK_THERMAL"])
        self.assertEqual(res_stu2.uncovered_personalized_skills, ["SK_CAN"])

    def test_27_deterministic_repeated_calls(self):
        """TEST 27: Deterministic output on repeated service calls."""
        res1 = self.service.get_course_candidates("STU_003", "ROLE_FULL_STACK_DEV").to_dict()
        res2 = self.service.get_course_candidates("STU_003", "ROLE_FULL_STACK_DEV").to_dict()
        self.assertEqual(res1, res2)

    def test_28_no_timestamps_in_results(self):
        """TEST 28: No dynamic timestamps or random IDs in service results."""
        res = self.service.get_course_candidates("STU_001", "ROLE_DATA_ENGINEER").to_dict()
        self.assertNotIn("timestamp", res)
        self.assertNotIn("uuid", res)
        self.assertNotIn("created_at", res)

    def test_29_no_raw_data_dependency(self):
        """TEST 29: Service operates strictly on validated artifacts / runtime input."""
        for path in [PATH_DEMAND, PATH_EVIDENCE, PATH_GENERIC_REC, PATH_COURSE_SELECTION]:
            self.assertTrue(path.exists())

    def test_30_synthetic_demo_mode_identification(self):
        """TEST 30: Synthetic/demo mode is explicitly declared on artifact-backed results."""
        res_dem = self.service.get_skill_demand()
        self.assertTrue(res_dem.is_synthetic_artifact)
        res_cand = self.service.get_course_candidates("STU_001", "ROLE_DATA_ENGINEER")
        self.assertTrue(res_cand.is_synthetic_artifact)

    def test_31_runtime_extraction_independent_of_artifacts(self):
        """TEST 31: Runtime extraction functions with zero artifact dependencies."""
        res = self.service.extract_skills("Python and SQL")
        self.assertEqual(len(res), 2)

    def test_32_runtime_employer_analysis_independent(self):
        """TEST 32: Runtime employer analysis functions with zero demand artifact dependency."""
        fb = {"feedback_id": "FB_1", "employer_id": "E1", "course_id": 42, "rating": 5, "comments": "Good BMS knowledge"}
        res = self.service.analyze_employer_feedback(fb)
        self.assertFalse(res.is_synthetic_artifact)

    def test_33_service_package_no_backend_import(self):
        """TEST 33: ml/api does not import backend modules."""
        import ml.api.service as s_mod
        source = inspect.getsource(s_mod)
        for forbidden in ["backend", "app", "routers", "controllers", "crud"]:
            self.assertNotIn(f"import {forbidden}", source)
            self.assertNotIn(f"from {forbidden}", source)

    def test_34_service_package_no_frontend_import(self):
        """TEST 34: ml/api does not import frontend modules."""
        import ml.api.service as s_mod
        source = inspect.getsource(s_mod)
        for forbidden in ["frontend", "ui", "components", "static"]:
            self.assertNotIn(f"import {forbidden}", source)
            self.assertNotIn(f"from {forbidden}", source)

    def test_35_handoff_document_exists(self):
        """TEST 35: ML_BACKEND_HANDOFF.md exists and documents public functions."""
        handoff_path = Path(__file__).resolve().parent.parent / "ML_BACKEND_HANDOFF.md"
        self.assertTrue(handoff_path.exists())
        with open(handoff_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("extract_skills", content)
        self.assertIn("process_job", content)
        self.assertIn("get_skill_demand", content)
        self.assertIn("get_course_skill_gaps", content)
        self.assertIn("analyze_employer_feedback", content)
        self.assertIn("get_skill_evidence", content)
        self.assertIn("get_skill_recommendations", content)
        self.assertIn("get_role_skill_context", content)
        self.assertIn("get_student_skill_profile", content)
        self.assertIn("get_student_skill_gap", content)
        self.assertIn("get_personalized_recommendations", content)
        self.assertIn("get_course_candidates", content)

    def test_36_deterministic_return_structures(self):
        """TEST 36: All public service functions have dataclass/dict return models."""
        self.assertIsInstance(self.service.get_skill_demand(), SkillDemandResult)
        self.assertIsInstance(self.service.get_course_skill_gaps(), CourseGapResult)
        self.assertIsInstance(self.service.get_skill_evidence(), SkillEvidenceResult)
        self.assertIsInstance(self.service.get_skill_recommendations(), SkillRecommendationResult)
        self.assertIsInstance(self.service.get_role_skill_context("ROLE_DATA_ENGINEER"), RoleSkillContextResult)
        self.assertIsInstance(self.service.get_student_skill_profile("STU_001"), StudentProfileResult)
        self.assertIsInstance(self.service.get_student_skill_gap("STU_001", "ROLE_DATA_ENGINEER"), StudentGapResult)
        self.assertIsInstance(self.service.get_personalized_recommendations("STU_001", "ROLE_DATA_ENGINEER"), PersonalizedRecommendationResult)
        self.assertIsInstance(self.service.get_course_candidates("STU_001", "ROLE_DATA_ENGINEER"), CourseCandidateResult)

    def test_37_explicit_centralized_artifact_paths(self):
        """TEST 37: Artifact paths in service.py are explicit and centralized."""
        for p in [PATH_DEMAND, PATH_COURSE_GAP, PATH_EMPLOYER_FEEDBACK, PATH_EVIDENCE,
                  PATH_GENERIC_REC, PATH_CONTEXT_REC, PATH_STUDENT_PROFILE,
                  PATH_STUDENT_GAP, PATH_PERSONALIZED_REC, PATH_COURSE_SELECTION]:
            self.assertTrue(p.name.endswith(".json"))

    def test_38_course_candidate_results_ordering(self):
        """TEST 38: Course candidate results preserve 7E ordering (course_id ASC)."""
        res = self.service.get_course_candidates("STU_003", "ROLE_FULL_STACK_DEV")
        c_ids = [c["course_id"] for c in res.candidate_courses]
        self.assertEqual(c_ids, sorted(c_ids))

    def test_39_personalized_recommendations_ordering(self):
        """TEST 39: Personalized recommendation results preserve 7C ordering (skill_id ASC)."""
        res = self.service.get_personalized_recommendations("STU_001", "ROLE_DATA_ENGINEER")
        s_ids = [r["skill_id"] for r in res.skill_recommendations]
        self.assertEqual(s_ids, sorted(s_ids))

if __name__ == "__main__":
    unittest.main()
