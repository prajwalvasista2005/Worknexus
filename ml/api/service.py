import os
import sys
import json
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from .models import (
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

# Canonical Artifact Paths
ML_BASE_DIR = Path(__file__).resolve().parent.parent

PATH_TAXONOMY = ML_BASE_DIR / "data" / "skills.json"
PATH_SAMPLE_COURSES = ML_BASE_DIR / "data" / "sample_courses.json"
PATH_DEMAND = ML_BASE_DIR / "demand" / "demand_analysis.json"
PATH_COURSE_GAP = ML_BASE_DIR / "gap" / "skill_gap_analysis.json"
PATH_EMPLOYER_FEEDBACK = ML_BASE_DIR / "employer" / "employer_feedback_analysis.json"
PATH_EVIDENCE = ML_BASE_DIR / "evidence" / "multi_signal_evidence.json"
PATH_GENERIC_REC = ML_BASE_DIR / "recommend" / "skill_recommendations.json"
PATH_CONTEXT_REC = ML_BASE_DIR / "context" / "contextual_recommendations.json"
PATH_STUDENT_PROFILE = ML_BASE_DIR / "student" / "student_skill_profiles.json"
PATH_STUDENT_GAP = ML_BASE_DIR / "gap_student" / "student_skill_gaps.json"
PATH_PERSONALIZED_REC = ML_BASE_DIR / "personalized" / "student_skill_recommendations.json"
PATH_COURSE_SELECTION = ML_BASE_DIR / "course_selection" / "course_selection_candidates.json"

class MLService:
    """
    Public Service Layer Interface for the WorkNexus ML Engine.
    Exposes deterministic, type-safe Python methods for skill extraction,
    demand analysis, evidence aggregation, recommendations, and course mapping.
    Acts as the single integration point for the core backend.
    """

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or ML_BASE_DIR
        self._load_taxonomy()

    def _load_taxonomy(self):
        tax_file = self.base_dir / "data" / "skills.json"
        if not tax_file.exists():
            raise ArtifactNotFoundError(f"Canonical taxonomy not found at {tax_file}")
        with open(tax_file, "r", encoding="utf-8") as f:
            self._taxonomy_data = json.load(f)
        self.valid_skill_ids = {s["id"] for s in self._taxonomy_data}

    def _load_artifact(self, artifact_path: Path) -> Dict[str, Any]:
        if not artifact_path.exists():
            raise ArtifactNotFoundError(f"Required ML artifact missing: {artifact_path}")
        try:
            with open(artifact_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise SchemaValidationError(f"Malformed JSON artifact at {artifact_path}: {e}")

    # =================================================================
    # 1. SKILL EXTRACTION (Runtime Input)
    # =================================================================
    def extract_skills(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract canonical skill IDs and confidence scores from raw text.
        Frozen contract: returns List[Dict[str, Any]] containing exactly 'skill_id' and 'confidence_score'.
        """
        if not isinstance(text, str):
            raise InvalidInputError(f"extract_skills expects text of type str, got {type(text).__name__}")
        
        from ml.extract.extractor import extract_skills as _extract
        raw_results = _extract(text)
        
        return [
            {
                "skill_id": r["skill_id"],
                "confidence_score": float(r["confidence_score"])
            }
            for r in raw_results
        ]

    # =================================================================
    # 2. JOB PROCESSING (Runtime Input)
    # =================================================================
    def process_job(self, job: Union[Dict[str, Any], Any]) -> JobProcessingResult:
        """
        Process a single job record to extract canonical skills.
        Accepts dictionary or object with 'title', 'description', 'company', 'location'.
        """
        if isinstance(job, dict):
            job_id = str(job.get("id", job.get("job_id", "JOB_UNKNOWN")))
            title = str(job.get("title", ""))
            company = str(job.get("company", ""))
            location = str(job.get("location", ""))
            description = str(job.get("description", ""))
        elif hasattr(job, "title") and hasattr(job, "description"):
            job_id = getattr(job, "id", getattr(job, "job_id", "JOB_UNKNOWN"))
            title = getattr(job, "title", "")
            company = getattr(job, "company", "")
            location = getattr(job, "location", "")
            description = getattr(job, "description", "")
        else:
            raise InvalidInputError("job input must be a dictionary or object with title and description")

        combined_text = f"{title}\n{description}"
        extracted = self.extract_skills(combined_text)

        return JobProcessingResult(
            job_id=job_id,
            title=title,
            company=company,
            location=location,
            extracted_skills=extracted,
            total_skills_extracted=len(extracted)
        )

    # =================================================================
    # 3. DEMAND ANALYSIS (Artifact / Benchmark Mode)
    # =================================================================
    def get_skill_demand(self) -> SkillDemandResult:
        """
        Retrieve validated skill demand statistics aggregated across observed job postings (Phase 3).
        """
        data = self._load_artifact(PATH_DEMAND)
        meta = data.get("metadata", {})
        skills = data.get("skills", [])
        cat_demand = data.get("category_demand", data.get("category_breakdown", {}))
        src_dist = data.get("source_distribution", {})

        return SkillDemandResult(
            total_jobs_analyzed=meta.get("total_jobs", 0),
            total_unique_skills_demanded=meta.get("unique_skills_detected", len(skills)),
            top_skills=skills[:10],
            category_demand=cat_demand,
            source_distribution=src_dist,
            is_synthetic_artifact=True
        )

    # =================================================================
    # 4. COURSE GAP ANALYSIS (Artifact / Benchmark Mode)
    # =================================================================
    def get_course_skill_gaps(self) -> CourseGapResult:
        """
        Retrieve curriculum vs industry demand coverage analysis (Phase 4).
        """
        data = self._load_artifact(PATH_COURSE_GAP)
        meta = data.get("metadata", {})
        courses = data.get("courses", [])

        return CourseGapResult(
            total_courses_analyzed=meta.get("total_courses", len(courses)),
            total_skills_demanded=meta.get("observed_demand_skills", 0),
            overall_taught_coverage_ratio=meta.get("overall_taught_coverage_ratio", 0.0),
            course_gaps=courses,
            is_synthetic_artifact=True
        )

    # =================================================================
    # 5. EMPLOYER FEEDBACK ANALYSIS (Runtime & Artifact Mode)
    # =================================================================
    def analyze_employer_feedback(self, feedback: Union[List[Dict[str, Any]], Dict[str, Any]]) -> EmployerFeedbackResult:
        """
        Analyze structured employer feedback records extracting skills from comment text (Phase 5A).
        """
        from ml.employer.feedback_analyzer import EmployerFeedbackAnalyzer

        records = [feedback] if isinstance(feedback, dict) else feedback
        if not isinstance(records, list):
            raise InvalidInputError("feedback input must be a dictionary or list of dictionaries")

        # Validate structure and normalize comment keys
        normalized_records = []
        for rec in records:
            if not isinstance(rec, dict):
                raise InvalidInputError("Each feedback record must be a dictionary")
            fb_id = str(rec.get("feedback_id", rec.get("id", "FB_UNKNOWN")))
            text = rec.get("comments") or rec.get("comment") or rec.get("feedback_text") or ""
            emp_id = rec.get("employer_id", "EMP_UNKNOWN")
            course_id = rec.get("course_id")
            trust = rec.get("trust_weight", 1.0)
            
            normalized_records.append({
                "feedback_id": fb_id,
                "employer_id": emp_id,
                "course_id": course_id,
                "trust_weight": trust,
                "comment": text
            })

        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json", encoding="utf-8") as f:
            json.dump(normalized_records, f)
            temp_path = Path(f.name)

        try:
            analyzer = EmployerFeedbackAnalyzer(feedback_path=temp_path, taxonomy_path=PATH_TAXONOMY)
            res = analyzer.analyze()
        finally:
            if temp_path.exists():
                temp_path.unlink()

        return EmployerFeedbackResult(
            total_feedback_records=len(records),
            detected_skills=res.get("skill_signals", []),
            course_signals=res.get("course_signals", []),
            is_synthetic_artifact=False
        )

    # =================================================================
    # 6. MULTI-SIGNAL EVIDENCE (Artifact / Benchmark Mode)
    # =================================================================
    def get_skill_evidence(self) -> SkillEvidenceResult:
        """
        Retrieve combined job market demand and employer feedback evidence (Phase 5B).
        """
        data = self._load_artifact(PATH_EVIDENCE)
        meta = data.get("metadata", {})
        skills = data.get("skills", [])

        return SkillEvidenceResult(
            total_skills_evaluated=meta.get("union_skill_count", len(skills)),
            multi_signal_skills=skills,
            is_synthetic_artifact=True
        )

    # =================================================================
    # 7. GENERIC SKILL RECOMMENDATIONS (Artifact / Benchmark Mode)
    # =================================================================
    def get_skill_recommendations(self) -> SkillRecommendationResult:
        """
        Retrieve transparent, rule-based generic skill recommendations (Phase 6A).
        """
        data = self._load_artifact(PATH_GENERIC_REC)
        meta = data.get("metadata", {})
        recs = data.get("recommendations", [])

        recommended = [
            r for r in recs
            if r.get("recommendation", {}).get("status") == "recommended"
        ]
        not_recommended = [
            r for r in recs
            if r.get("recommendation", {}).get("status") == "not_recommended"
        ]

        return SkillRecommendationResult(
            total_skills_evaluated=meta.get("total_skills", len(recs)),
            recommended_skills=recommended,
            not_recommended_skills=not_recommended,
            is_synthetic_artifact=True
        )

    # =================================================================
    # 8. ROLE-CONTEXT RECOMMENDATIONS (Artifact / Benchmark Mode)
    # =================================================================
    def get_role_skill_context(self, role_id: str) -> RoleSkillContextResult:
        """
        Retrieve contextual skill recommendations for an explicitly defined target role (Phase 6B).
        """
        if not isinstance(role_id, str) or not role_id.strip():
            raise InvalidInputError("role_id must be a non-empty string")

        data = self._load_artifact(PATH_CONTEXT_REC)
        roles = data.get("roles", [])

        matched_role = next((r for r in roles if r.get("role_id") == role_id), None)
        if not matched_role:
            valid_roles = [r.get("role_id") for r in roles]
            raise UnknownRoleError(f"Role ID '{role_id}' not recognized. Available roles: {valid_roles}")

        summary = {
            "target_skill_count": matched_role.get("target_skill_count", 0),
            "recommended_target_skill_count": matched_role.get("recommended_target_skill_count", 0),
            "not_recommended_target_skill_count": matched_role.get("not_recommended_target_skill_count", 0),
            "unavailable_target_skill_count": matched_role.get("unavailable_target_skill_count", 0)
        }

        return RoleSkillContextResult(
            role_id=matched_role["role_id"],
            role_name=matched_role.get("role_name", ""),
            contextual_recommendations=matched_role.get("role_skill_context", []),
            summary=summary,
            is_synthetic_artifact=True
        )

    # =================================================================
    # 9. STUDENT PROFILE (Artifact / Benchmark Mode)
    # =================================================================
    def get_student_skill_profile(self, student_id: str) -> StudentProfileResult:
        """
        Retrieve normalized canonical skill profile for a student (Phase 7A).
        """
        if not isinstance(student_id, str) or not student_id.strip():
            raise InvalidInputError("student_id must be a non-empty string")

        data = self._load_artifact(PATH_STUDENT_PROFILE)
        students = data.get("students", [])

        matched_stu = next((s for s in students if s.get("student_id") == student_id), None)
        if not matched_stu:
            valid_students = [s.get("student_id") for s in students]
            raise UnknownStudentError(f"Student ID '{student_id}' not found. Available: {valid_students}")

        summary = {
            "skill_count": matched_stu.get("skill_count", len(matched_stu.get("skills", [])))
        }

        return StudentProfileResult(
            student_id=matched_stu["student_id"],
            profile_skills=matched_stu.get("skills", []),
            summary=summary,
            is_synthetic_artifact=True
        )

    # =================================================================
    # 10. STUDENT GAP (Artifact / Benchmark Mode)
    # =================================================================
    def get_student_skill_gap(self, student_id: str, role_id: str) -> StudentGapResult:
        """
        Retrieve student-to-target-role skill gap analysis (Phase 7B).
        """
        if not isinstance(student_id, str) or not student_id.strip():
            raise InvalidInputError("student_id must be a non-empty string")
        if not isinstance(role_id, str) or not role_id.strip():
            raise InvalidInputError("role_id must be a non-empty string")

        data = self._load_artifact(PATH_STUDENT_GAP)
        students = data.get("students", [])

        matched_stu = next((s for s in students if s.get("student_id") == student_id), None)
        if not matched_stu:
            valid_students = [s.get("student_id") for s in students]
            raise UnknownStudentError(f"Student ID '{student_id}' not found. Available: {valid_students}")

        assigned_role = matched_stu.get("role", {})
        if assigned_role.get("role_id") != role_id:
            raise UnknownRoleError(
                f"Student '{student_id}' is assigned to role '{assigned_role.get('role_id')}', not '{role_id}'"
            )

        return StudentGapResult(
            student_id=matched_stu["student_id"],
            role=assigned_role,
            skill_gaps=matched_stu.get("skill_gaps", []),
            summary=matched_stu.get("summary", {}),
            is_synthetic_artifact=True
        )

    # =================================================================
    # 11. PERSONALIZED RECOMMENDATIONS (Artifact / Benchmark Mode)
    # =================================================================
    def get_personalized_recommendations(self, student_id: str, role_id: str) -> PersonalizedRecommendationResult:
        """
        Retrieve personalized skill development recommendations for a student and assigned role (Phase 7C).
        """
        if not isinstance(student_id, str) or not student_id.strip():
            raise InvalidInputError("student_id must be a non-empty string")
        if not isinstance(role_id, str) or not role_id.strip():
            raise InvalidInputError("role_id must be a non-empty string")

        data = self._load_artifact(PATH_PERSONALIZED_REC)
        students = data.get("students", [])

        matched_stu = next((s for s in students if s.get("student_id") == student_id), None)
        if not matched_stu:
            valid_students = [s.get("student_id") for s in students]
            raise UnknownStudentError(f"Student ID '{student_id}' not found. Available: {valid_students}")

        assigned_role = matched_stu.get("role", {})
        if assigned_role.get("role_id") != role_id:
            raise UnknownRoleError(
                f"Student '{student_id}' is assigned to role '{assigned_role.get('role_id')}', not '{role_id}'"
            )

        return PersonalizedRecommendationResult(
            student_id=matched_stu["student_id"],
            role=assigned_role,
            skill_recommendations=matched_stu.get("skill_recommendations", []),
            summary=matched_stu.get("summary", {}),
            is_synthetic_artifact=True
        )

    # =================================================================
    # 12. COURSE CANDIDATES (Artifact / Benchmark Mode)
    # =================================================================
    def get_course_candidates(self, student_id: str, role_id: str) -> CourseCandidateResult:
        """
        Retrieve candidate courses that cover personalized skill recommendations for a student (Phase 7E).
        """
        if not isinstance(student_id, str) or not student_id.strip():
            raise InvalidInputError("student_id must be a non-empty string")
        if not isinstance(role_id, str) or not role_id.strip():
            raise InvalidInputError("role_id must be a non-empty string")

        data = self._load_artifact(PATH_COURSE_SELECTION)
        students = data.get("students", [])

        matched_stu = next((s for s in students if s.get("student_id") == student_id), None)
        if not matched_stu:
            valid_students = [s.get("student_id") for s in students]
            raise UnknownStudentError(f"Student ID '{student_id}' not found. Available: {valid_students}")

        assigned_role = matched_stu.get("role", {})
        if assigned_role.get("role_id") != role_id:
            raise UnknownRoleError(
                f"Student '{student_id}' is assigned to role '{assigned_role.get('role_id')}', not '{role_id}'"
            )

        return CourseCandidateResult(
            student_id=matched_stu["student_id"],
            role=assigned_role,
            personalized_skill_ids=matched_stu.get("personalized_skill_ids", []),
            candidate_courses=matched_stu.get("candidate_courses", []),
            uncovered_personalized_skills=matched_stu.get("uncovered_personalized_skills", []),
            summary=matched_stu.get("summary", {}),
            is_synthetic_artifact=True
        )

    # =================================================================
    # 13. LIVE INTELLIGENCE COMPUTATION (Pure Python Engines)
    # =================================================================
    def compute_skill_demand(
        self,
        jobs: List[Dict[str, Any]],
        total_jobs: Optional[int] = None
    ) -> SkillDemandResult:
        """
        Compute live skill demand statistics from database job records (Phase 9B).
        Preserves Phase 3 job-based distinct counting and zero-skill denominator semantics.
        """
        from collections import defaultdict
        
        actual_total = total_jobs if total_jobs is not None else len(jobs)
        if actual_total == 0:
            return SkillDemandResult(
                total_jobs_analyzed=0,
                total_unique_skills_demanded=0,
                top_skills=[],
                category_demand={},
                source_distribution={},
                is_synthetic_artifact=False
            )

        taxonomy_map = {s["id"]: s for s in self._taxonomy_data}
        skill_counts: Dict[str, int] = defaultdict(int)
        skill_conf_sum: Dict[str, float] = defaultdict(float)
        category_jobs: Dict[str, set] = defaultdict(set)
        source_counts: Dict[str, int] = defaultdict(int)

        for job in jobs:
            job_id = str(job.get("job_id", job.get("id", "")))
            source = str(job.get("source", "worknexus_db"))
            source_counts[source] += 1

            skills = job.get("skills", [])
            seen_in_job = set()
            for s in skills:
                sk_id = s.get("skill_id") if isinstance(s, dict) else getattr(s, "skill_id", None)
                conf = float(s.get("confidence_score", 1.0) if isinstance(s, dict) else getattr(s, "confidence_score", 1.0))
                if sk_id and sk_id in taxonomy_map and sk_id not in seen_in_job:
                    seen_in_job.add(sk_id)
                    skill_counts[sk_id] += 1
                    skill_conf_sum[sk_id] += conf
                    cat = taxonomy_map[sk_id]["category"]
                    category_jobs[cat].add(job_id)

        top_skills = []
        for sk_id, count in sorted(skill_counts.items(), key=lambda x: (-x[1], x[0])):
            sk_info = taxonomy_map[sk_id]
            top_skills.append({
                "skill_id": sk_id,
                "skill_name": sk_info["name"],
                "category": sk_info["category"],
                "job_count": count,
                "demand_share": round(count / actual_total, 4),
                "average_confidence": round(skill_conf_sum[sk_id] / count, 4)
            })

        category_demand = {cat: len(job_set) for cat, job_set in category_jobs.items()}

        return SkillDemandResult(
            total_jobs_analyzed=actual_total,
            total_unique_skills_demanded=len(top_skills),
            top_skills=top_skills,
            category_demand=category_demand,
            source_distribution=dict(source_counts),
            is_synthetic_artifact=False
        )

    def compute_course_skill_gaps(
        self,
        courses: List[Dict[str, Any]],
        demand_data: Union[SkillDemandResult, Dict[str, Any]]
    ) -> CourseGapResult:
        """
        Compute live curriculum vs industry demand coverage analysis (Phase 9B).
        Preserves Phase 4 coverage metrics and factual gap classifications.
        """
        top_skills = demand_data.top_skills if isinstance(demand_data, SkillDemandResult) else demand_data.get("skills", demand_data.get("top_skills", []))
        demand_map = {s["skill_id"]: s.get("job_count", 0) for s in top_skills}
        demanded_skill_ids = set(demand_map.keys())
        total_observed_demand = sum(demand_map.values())

        course_gaps = []
        global_covered_skills = set()

        for c in courses:
            c_id = c.get("course_id", c.get("id"))
            c_name = c.get("course_name", c.get("name", f"Course {c_id}"))
            taught_skills = list(c.get("taught_skills", []))
            
            covered = sorted([s for s in taught_skills if s in demanded_skill_ids])
            missing = sorted([s for s in demanded_skill_ids if s not in taught_skills])
            not_in_demand = sorted([s for s in taught_skills if s not in demanded_skill_ids])

            covered_demand = sum(demand_map.get(s, 0) for s in covered)
            demand_cov = round(covered_demand / total_observed_demand, 4) if total_observed_demand > 0 else 0.0
            skill_cov = round(len(covered) / len(demanded_skill_ids), 4) if len(demanded_skill_ids) > 0 else 0.0

            for s in covered:
                global_covered_skills.add(s)

            course_gaps.append({
                "course_id": c_id,
                "course_name": c_name,
                "taught_skills_count": len(taught_skills),
                "covered_demand_skills_count": len(covered),
                "missing_demand_skills_count": len(missing),
                "demand_coverage_ratio": demand_cov,
                "skill_coverage_ratio": skill_cov,
                "covered_skills": covered,
                "missing_skills": missing,
                "course_skills_without_observed_demand": not_in_demand
            })

        overall_ratio = round(len(global_covered_skills) / len(demanded_skill_ids), 4) if len(demanded_skill_ids) > 0 else 0.0

        return CourseGapResult(
            total_courses_analyzed=len(courses),
            total_skills_demanded=len(demanded_skill_ids),
            overall_taught_coverage_ratio=overall_ratio,
            course_gaps=course_gaps,
            is_synthetic_artifact=False
        )

    def compute_skill_evidence(
        self,
        demand_data: Union[SkillDemandResult, Dict[str, Any]],
        employer_feedback_data: Union[EmployerFeedbackResult, Dict[str, Any], List[Dict[str, Any]]]
    ) -> SkillEvidenceResult:
        """
        Compute live multi-signal evidence combining job market demand and employer signals (Phase 9B).
        Preserves Phase 5B dual-signal evidence categories without artificial score mixing.
        """
        taxonomy_map = {s["id"]: s for s in self._taxonomy_data}

        # Index demand
        top_skills = demand_data.top_skills if isinstance(demand_data, SkillDemandResult) else demand_data.get("skills", demand_data.get("top_skills", []))
        demand_map = {s["skill_id"]: s for s in top_skills}

        # Index employer signals
        if isinstance(employer_feedback_data, EmployerFeedbackResult):
            emp_signals = employer_feedback_data.detected_skills
        elif isinstance(employer_feedback_data, dict):
            emp_signals = employer_feedback_data.get("detected_skills", employer_feedback_data.get("skill_signals", []))
        else:
            emp_signals = employer_feedback_data
        
        emp_map = {}
        for sig in emp_signals:
            sk_id = sig["skill_id"]
            emp_map[sk_id] = sig

        union_ids = sorted(list(set(demand_map.keys()) | set(emp_map.keys())))
        multi_signal_skills = []

        for sk_id in union_ids:
            sk_info = taxonomy_map.get(sk_id, {"name": sk_id, "category": "General"})
            in_dem = sk_id in demand_map
            in_emp = sk_id in emp_map

            if in_dem and in_emp:
                rel = "both"
            elif in_dem:
                rel = "job_only"
            else:
                rel = "employer_feedback_only"

            dem_rec = demand_map.get(sk_id)
            emp_rec = emp_map.get(sk_id)

            multi_signal_skills.append({
                "skill_id": sk_id,
                "skill_name": sk_info["name"],
                "category": sk_info["category"],
                "evidence_relationship": rel,
                "job_demand": {
                    "observed": in_dem,
                    "job_count": dem_rec["job_count"] if in_dem else 0,
                    "demand_share": dem_rec["demand_share"] if in_dem else 0.0
                },
                "employer_validation": {
                    "observed": in_emp,
                    "feedback_count": emp_rec.get("feedback_count", 1) if in_emp else 0,
                    "unique_employer_count": emp_rec.get("unique_employer_count", 1) if in_emp else 0,
                    "weighted_signal_sum": emp_rec.get("weighted_signal_sum", emp_rec.get("weighted_signal", 0.0)) if in_emp else 0.0
                }
            })

        return SkillEvidenceResult(
            total_skills_evaluated=len(multi_signal_skills),
            multi_signal_skills=multi_signal_skills,
            is_synthetic_artifact=False
        )

    def compute_skill_recommendations(
        self,
        evidence_data: Union[SkillEvidenceResult, Dict[str, Any]],
        course_gap_data: Union[CourseGapResult, Dict[str, Any]]
    ) -> SkillRecommendationResult:
        """
        Compute live transparent rule-based skill recommendations (Phase 9B).
        Preserves Phase 6A boolean conditions and machine-readable reason IDs.
        """
        skills_evidence = evidence_data.multi_signal_skills if isinstance(evidence_data, SkillEvidenceResult) else evidence_data.get("skills", evidence_data.get("multi_signal_skills", []))
        course_gaps = course_gap_data.course_gaps if isinstance(course_gap_data, CourseGapResult) else course_gap_data.get("courses", course_gap_data.get("course_gaps", []))

        covered_in_curriculum = set()
        for c in course_gaps:
            for s in c.get("covered_skills", []):
                covered_in_curriculum.add(s)

        recommended = []
        not_recommended = []

        for item in skills_evidence:
            sk_id = item["skill_id"]
            dem_obs = item.get("job_demand", {}).get("observed", False)
            emp_obs = item.get("employer_validation", {}).get("observed", False)
            course_cov = sk_id in covered_in_curriculum

            # Rule conditions (Phase 6A)
            # Condition 1: market_demand and employer_validation
            # Condition 2: market_demand and not course_coverage
            # Condition 3: employer_validation and not market_demand
            reasons = []
            is_rec = False

            if dem_obs and emp_obs:
                is_rec = True
                reasons.extend(["observed_market_demand", "employer_validated", "observed_in_both_sources"])
            elif dem_obs and not course_cov:
                is_rec = True
                reasons.extend(["observed_market_demand", "course_coverage_gap"])
            elif emp_obs and not dem_obs:
                is_rec = True
                reasons.extend(["employer_only_signal", "employer_validated"])

            rec_entry = {
                "skill_id": sk_id,
                "skill_name": item["skill_name"],
                "category": item["category"],
                "recommendation": {
                    "status": "recommended" if is_rec else "not_recommended",
                    "reasons": reasons if is_rec else ["insufficient_evidence_or_already_covered"]
                },
                "evidence_context": {
                    "job_demand": item.get("job_demand", {}),
                    "employer_validation": item.get("employer_validation", {}),
                    "taught_in_curriculum": course_cov
                }
            }

            if is_rec:
                recommended.append(rec_entry)
            else:
                not_recommended.append(rec_entry)

        return SkillRecommendationResult(
            total_skills_evaluated=len(skills_evidence),
            recommended_skills=sorted(recommended, key=lambda x: x["skill_id"]),
            not_recommended_skills=sorted(not_recommended, key=lambda x: x["skill_id"]),
            is_synthetic_artifact=False
        )

    def compute_role_skill_context(
        self,
        role_data: Dict[str, Any],
        generic_recommendations: Union[SkillRecommendationResult, Dict[str, Any]],
        all_evidence: Optional[Union[SkillEvidenceResult, Dict[str, Any]]] = None
    ) -> RoleSkillContextResult:
        """
        Compute live contextual skill recommendations for a target role (Phase 10B).
        Preserves Phase 6B explicit role grounding and 3-tier classification without scores.
        """
        taxonomy_map = {s["id"]: s for s in self._taxonomy_data}

        # Index generic recommendations
        if isinstance(generic_recommendations, SkillRecommendationResult):
            recs = generic_recommendations.recommended_skills
            not_recs = generic_recommendations.not_recommended_skills
        else:
            all_recs = generic_recommendations.get("recommendations", [])
            recs = [r for r in all_recs if r.get("recommendation", {}).get("status") == "recommended"]
            not_recs = [r for r in all_recs if r.get("recommendation", {}).get("status") == "not_recommended"]

        rec_map = {r["skill_id"]: r for r in recs}
        not_rec_map = {r["skill_id"]: r for r in not_recs}

        role_id = str(role_data.get("role_id", role_data.get("id", "")))
        role_name = str(role_data.get("role_name", role_data.get("name", role_id)))
        required_skills = list(role_data.get("required_skills", role_data.get("skill_ids", [])))

        contextual_recs = []
        rec_count = 0
        not_rec_count = 0
        unavail_count = 0

        for sk_id in sorted(required_skills):
            sk_info = taxonomy_map.get(sk_id, {"name": sk_id, "category": "General"})

            if sk_id in rec_map:
                status = "recommended"
                reasons = ["explicit_role_skill_mapping"]
                ev_context = rec_map[sk_id].get("evidence_context", {})
                rec_count += 1
            elif sk_id in not_rec_map:
                status = "not_recommended"
                reasons = ["role_mapping_without_generic_recommendation"]
                ev_context = not_rec_map[sk_id].get("evidence_context", {})
                not_rec_count += 1
            else:
                status = "not_available"
                reasons = ["role_skill_not_in_evidence_universe"]
                ev_context = {
                    "job_demand": {"observed": False, "job_count": 0, "demand_share": 0.0},
                    "employer_validation": {"observed": False, "feedback_count": 0, "unique_employer_count": 0, "weighted_signal_sum": 0.0},
                    "taught_in_curriculum": False
                }
                unavail_count += 1

            contextual_recs.append({
                "skill_id": sk_id,
                "skill_name": sk_info["name"],
                "category": sk_info["category"],
                "contextual_recommendation_status": status,
                "recommendation": {
                    "status": status,
                    "reasons": reasons
                },
                "evidence_context": ev_context
            })

        summary = {
            "target_skill_count": len(required_skills),
            "recommended_target_skill_count": rec_count,
            "not_recommended_target_skill_count": not_rec_count,
            "unavailable_target_skill_count": unavail_count
        }

        return RoleSkillContextResult(
            role_id=role_id,
            role_name=role_name,
            contextual_recommendations=contextual_recs,
            summary=summary,
            is_synthetic_artifact=False
        )

    def compute_student_skill_profile(
        self,
        student_id: str,
        evidence_records: List[Dict[str, Any]]
    ) -> StudentProfileResult:
        """
        Compute live normalized student skill profile from database evidence (Phase 10B).
        Preserves Phase 7A multi-source evidence provenance without numerical scoring.
        """
        from collections import defaultdict
        taxonomy_map = {s["id"]: s for s in self._taxonomy_data}

        grouped_evidence: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for ev in evidence_records:
            sk_id = ev.get("skill_id")
            if sk_id:
                grouped_evidence[sk_id].append({
                    "evidence_type": ev.get("evidence_type", ev.get("type", "self_reported")),
                    "evidence_strength": ev.get("strength", ev.get("evidence_strength", "intermediate")),
                    **ev.get("metadata", {})
                })

        profile_skills = []
        for sk_id in sorted(grouped_evidence.keys()):
            sk_info = taxonomy_map.get(sk_id, {"name": sk_id, "category": "General"})
            profile_skills.append({
                "skill_id": sk_id,
                "skill_name": sk_info["name"],
                "category": sk_info["category"],
                "evidence": grouped_evidence[sk_id]
            })

        summary = {
            "skill_count": len(profile_skills)
        }

        return StudentProfileResult(
            student_id=str(student_id),
            profile_skills=profile_skills,
            summary=summary,
            is_synthetic_artifact=False
        )

    def compute_student_skill_gap(
        self,
        student_profile: Union[StudentProfileResult, Dict[str, Any]],
        role_context: Union[RoleSkillContextResult, Dict[str, Any]]
    ) -> StudentGapResult:
        """
        Compute live student-to-target-role skill gap analysis (Phase 10B).
        Preserves Phase 7B present/missing semantics and contextual evidence integrity without gap scores.
        """
        stu_id = student_profile.student_id if isinstance(student_profile, StudentProfileResult) else student_profile.get("student_id", "")
        profile_skills = student_profile.profile_skills if isinstance(student_profile, StudentProfileResult) else student_profile.get("skills", student_profile.get("profile_skills", []))
        
        student_skill_ids = {s["skill_id"] for s in profile_skills}
        student_evidence_map = {s["skill_id"]: s.get("evidence", []) for s in profile_skills}

        role_id = role_context.role_id if isinstance(role_context, RoleSkillContextResult) else role_context.get("role_id", "")
        role_name = role_context.role_name if isinstance(role_context, RoleSkillContextResult) else role_context.get("role_name", role_id)
        role_recs = role_context.contextual_recommendations if isinstance(role_context, RoleSkillContextResult) else role_context.get("contextual_recommendations", role_context.get("role_skill_context", []))

        skill_gaps = []
        present_count = 0
        missing_count = 0

        for item in role_recs:
            sk_id = item["skill_id"]
            is_present = sk_id in student_skill_ids
            stu_status = "present" if is_present else "missing"
            
            if is_present:
                present_count += 1
            else:
                missing_count += 1

            context_status = item.get("contextual_recommendation_status", item.get("recommendation", {}).get("status", "not_available"))

            skill_gaps.append({
                "skill_id": sk_id,
                "skill_name": item["skill_name"],
                "category": item["category"],
                "student_status": stu_status,
                "student_evidence": student_evidence_map.get(sk_id, []) if is_present else [],
                "contextual_recommendation_status": context_status,
                "evidence_context": item.get("evidence_context", {})
            })

        summary = {
            "total_role_skills": len(skill_gaps),
            "present_skills_count": present_count,
            "missing_skills_count": missing_count
        }

        return StudentGapResult(
            student_id=str(stu_id),
            role={"role_id": role_id, "role_name": role_name},
            skill_gaps=skill_gaps,
            summary=summary,
            is_synthetic_artifact=False
        )

    def compute_personalized_recommendations(
        self,
        student_gap: Union[StudentGapResult, Dict[str, Any]],
        generic_recommendations: Union[SkillRecommendationResult, Dict[str, Any]],
        evidence_data: Optional[Union[SkillEvidenceResult, Dict[str, Any]]] = None
    ) -> PersonalizedRecommendationResult:
        """
        Compute live personalized skill recommendations for a student and role (Phase 10B).
        Preserves Phase 7C boolean logic: recommended iff missing + role_required + generic_recommended.
        """
        stu_id = student_gap.student_id if isinstance(student_gap, StudentGapResult) else student_gap.get("student_id", "")
        role = student_gap.role if isinstance(student_gap, StudentGapResult) else student_gap.get("role", {})
        gaps = student_gap.skill_gaps if isinstance(student_gap, StudentGapResult) else student_gap.get("skill_gaps", [])

        # Index generic recommendations
        if isinstance(generic_recommendations, SkillRecommendationResult):
            recs = generic_recommendations.recommended_skills
        else:
            all_recs = generic_recommendations.get("recommendations", [])
            recs = [r for r in all_recs if r.get("recommendation", {}).get("status") == "recommended"]

        generic_rec_map = {r["skill_id"]: r for r in recs}

        personalized_recs = []
        already_present_count = 0
        recommended_count = 0
        not_recommended_count = 0

        for gap in gaps:
            sk_id = gap["skill_id"]
            stu_status = gap["student_status"]
            context_status = gap.get("contextual_recommendation_status", "not_available")

            if stu_status == "present":
                status = "already_present"
                reasons = ["already_present"]
                already_present_count += 1
            else:
                # Actual missing role gap is recommended
                status = "recommended"
                reasons = ["student_skill_gap", "role_requirement"]
                if context_status == "recommended" or sk_id in generic_rec_map:
                    reasons.append("generic_evidence_recommended")
                    gen_rec = generic_rec_map.get(sk_id, {})
                    gen_reasons = gen_rec.get("recommendation", {}).get("reasons", [])
                    for gr in gen_reasons:
                        if gr in ["observed_market_demand", "employer_validated", "observed_in_both_sources", "course_coverage_gap", "employer_only_signal"]:
                            if gr == "observed_market_demand":
                                reasons.append("market_demand_evidence")
                            elif gr == "employer_validated":
                                reasons.append("employer_validation_evidence")
                            elif gr == "observed_in_both_sources":
                                reasons.append("multi_source_evidence")
                            elif gr == "course_coverage_gap":
                                reasons.append("course_coverage_gap")
                recommended_count += 1

            personalized_recs.append({
                "skill_id": sk_id,
                "skill_name": gap["skill_name"],
                "category": gap["category"],
                "student_status": stu_status,
                "personalized_status": status,
                "recommendation": {
                    "status": status,
                    "reasons": sorted(list(set(reasons)))
                },
                "evidence_context": gap.get("evidence_context", {})
            })

        summary = {
            "total_role_skills": len(personalized_recs),
            "already_present_count": already_present_count,
            "recommended_count": recommended_count,
            "not_recommended_count": not_recommended_count
        }

        return PersonalizedRecommendationResult(
            student_id=str(stu_id),
            role=role if isinstance(role, dict) else {"role_id": getattr(role, "role_id", ""), "role_name": getattr(role, "role_name", "")},
            skill_recommendations=personalized_recs,
            summary=summary,
            is_synthetic_artifact=False
        )

    def compute_course_candidates(
        self,
        personalized_recommendations: Union[PersonalizedRecommendationResult, Dict[str, Any]],
        courses: List[Dict[str, Any]]
    ) -> CourseCandidateResult:
        """
        Compute live candidate courses covering personalized skill recommendations (Phase 10B).
        Preserves rule: candidate iff course covers >= 1 personalized recommended or missing gap skill.
        """
        stu_id = personalized_recommendations.student_id if isinstance(personalized_recommendations, PersonalizedRecommendationResult) else personalized_recommendations.get("student_id", "")
        role = personalized_recommendations.role if isinstance(personalized_recommendations, PersonalizedRecommendationResult) else personalized_recommendations.get("role", {})
        recs = personalized_recommendations.skill_recommendations if isinstance(personalized_recommendations, PersonalizedRecommendationResult) else personalized_recommendations.get("skill_recommendations", [])

        # Collect target skill IDs: role gaps (missing skills) and recommended skills
        recommended_skill_ids = set()
        for r in recs:
            p_status = r.get("personalized_status", r.get("recommendation", {}).get("status"))
            stu_status = r.get("student_status", r.get("status"))
            sk_id = r.get("skill_id", r.get("id"))
            if p_status == "recommended" or stu_status == "missing" or p_status not in ["already_present", "present"]:
                if sk_id:
                    recommended_skill_ids.add(str(sk_id))

        # Also support direct missing_skills if passed in
        raw_missing = []
        if isinstance(personalized_recommendations, dict):
            raw_missing = personalized_recommendations.get("missing_skills", personalized_recommendations.get("skills_missing", []))
        elif hasattr(personalized_recommendations, "missing_skills"):
            raw_missing = getattr(personalized_recommendations, "missing_skills", [])

        for ms in raw_missing:
            if isinstance(ms, str):
                recommended_skill_ids.add(ms)
            elif isinstance(ms, dict):
                ms_id = ms.get("skill_id") or ms.get("id")
                if ms_id:
                    recommended_skill_ids.add(str(ms_id))

        candidate_courses = []
        globally_covered = set()

        for c in courses:
            c_id = c.get("course_id", c.get("id"))
            c_name = c.get("course_name", c.get("name", f"Course {c_id}"))
            raw_taught = c.get("taught_skills", c.get("skill_ids", []))
            taught = set()
            for s in raw_taught:
                if isinstance(s, dict):
                    taught.add(str(s.get("skill_id") or s.get("id", "")))
                else:
                    taught.add(str(s))
            covered_rec = sorted(list(taught & recommended_skill_ids))

            if len(covered_rec) >= 1:
                for s in covered_rec:
                    globally_covered.add(s)

                candidate_courses.append({
                    "course_id": c_id,
                    "course_name": c_name,
                    "covered_personalized_skills": covered_rec,
                    "covered_personalized_skills_count": len(covered_rec),
                    "total_taught_skills_count": len(taught)
                })

        uncovered = sorted(list(recommended_skill_ids - globally_covered))

        summary = {
            "total_personalized_recommended_skills": len(recommended_skill_ids),
            "candidate_courses_count": len(candidate_courses),
            "uncovered_personalized_skills_count": len(uncovered)
        }

        return CourseCandidateResult(
            student_id=str(stu_id),
            role=role if isinstance(role, dict) else {"role_id": getattr(role, "role_id", ""), "role_name": getattr(role, "role_name", "")},
            personalized_skill_ids=sorted(list(recommended_skill_ids)),
            candidate_courses=sorted(candidate_courses, key=lambda x: x["course_id"]),
            uncovered_personalized_skills=uncovered,
            summary=summary,
            is_synthetic_artifact=False
        )


