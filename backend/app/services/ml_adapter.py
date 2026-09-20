import logging
from typing import List, Dict, Any, Union, Optional

try:
    from fastapi import HTTPException, status
except ImportError:
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            self.status_code = status_code
            self.detail = detail
            super().__init__(f"HTTP {status_code}: {detail}")

    class status:
        HTTP_200_OK = 200
        HTTP_201_CREATED = 201
        HTTP_400_BAD_REQUEST = 400
        HTTP_401_UNAUTHORIZED = 401
        HTTP_403_FORBIDDEN = 403
        HTTP_404_NOT_FOUND = 404
        HTTP_422_UNPROCESSABLE_ENTITY = 422
        HTTP_500_INTERNAL_SERVER_ERROR = 500
        HTTP_501_NOT_IMPLEMENTED = 501

from ml.api import (
    MLService,
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
from .ml_data_service import MLDataService

logger = logging.getLogger(__name__)

class MLAdapter:
    """
    Unified In-Process Integration Adapter for the WorkNexus ML Engine.
    Serves as the exclusive bridge between the backend service layer and MLService.
    Converts backend domain objects into ML input contracts and translates
    ML domain exceptions into standard HTTP/service responses.
    """

    def __init__(self, service: Optional[MLService] = None):
        self._service = service or MLService()

    # =================================================================
    # 1. SKILL EXTRACTION (LIVE_READY)
    # =================================================================
    def extract_skills(self, text: str) -> List[Dict[str, Any]]:
        """Extract canonical skills and confidence tiers from raw text."""
        if not text or not isinstance(text, str):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Input text must be a non-empty string"
            )
        try:
            return self._service.extract_skills(text)
        except InvalidInputError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
        except MLError as e:
            logger.error(f"ML extraction error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="ML skill extraction failed"
            )

    # =================================================================
    # 2. JOB PROCESSING (LIVE_READY)
    # =================================================================
    def process_job(self, job: Union[Dict[str, Any], Any]) -> JobProcessingResult:
        """Process a job posting entity or dictionary, extracting canonical skills."""
        try:
            return self._service.process_job(job)
        except InvalidInputError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
        except MLError as e:
            logger.error(f"ML job processing error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="ML job processing failed"
            )

    # =================================================================
    # 3. EMPLOYER FEEDBACK ANALYSIS (LIVE_READY)
    # =================================================================
    def analyze_employer_feedback(
        self,
        feedback: Union[List[Dict[str, Any]], Dict[str, Any]]
    ) -> EmployerFeedbackResult:
        """Analyze structured employer feedback comments, computing trust-weighted signals."""
        try:
            return self._service.analyze_employer_feedback(feedback)
        except InvalidInputError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
        except MLError as e:
            logger.error(f"ML employer feedback analysis error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="ML employer feedback analysis failed"
            )

    # =================================================================
    # 4. SKILL DEMAND (LIVE_READY / BENCHMARK)
    # =================================================================
    def get_skill_demand(self, db=None, mode: str = "live") -> SkillDemandResult:
        """
        Retrieve skill demand intelligence.
        In 'live' mode: computes demand directly from live DB JobPosting records.
        In 'benchmark' mode: retrieves authoritative Phase 3 benchmark artifact.
        """
        if mode == "benchmark" or db is None:
            try:
                return self._service.get_skill_demand()
            except ArtifactNotFoundError as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
            except MLError as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"ML demand error: {e}")

        jobs_list, total_jobs = MLDataService.get_live_jobs_data(db)
        return self._service.compute_skill_demand(jobs=jobs_list, total_jobs=total_jobs)

    # =================================================================
    # 5. COURSE SKILL GAPS (LIVE_READY / BENCHMARK)
    # =================================================================
    def get_course_skill_gaps(self, db=None, mode: str = "live") -> CourseGapResult:
        """
        Retrieve course curriculum gap intelligence.
        In 'live' mode: computes gaps from live Course records and live demand.
        In 'benchmark' mode: retrieves authoritative Phase 4 benchmark artifact.
        """
        if mode == "benchmark" or db is None:
            try:
                return self._service.get_course_skill_gaps()
            except ArtifactNotFoundError as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
            except MLError as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"ML course gap error: {e}")

        demand_res = self.get_skill_demand(db=db, mode="live")
        courses_list = MLDataService.get_live_courses_data(db)
        return self._service.compute_course_skill_gaps(courses=courses_list, demand_data=demand_res)

    # =================================================================
    # 6. MULTI-SIGNAL EVIDENCE (LIVE_READY / BENCHMARK)
    # =================================================================
    def get_skill_evidence(self, db=None, mode: str = "live") -> SkillEvidenceResult:
        """
        Retrieve combined job market demand and employer feedback evidence.
        In 'live' mode: combines live job demand and live employer signals.
        In 'benchmark' mode: retrieves authoritative Phase 5B benchmark artifact.
        """
        if mode == "benchmark" or db is None:
            try:
                return self._service.get_skill_evidence()
            except ArtifactNotFoundError as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
            except MLError as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"ML evidence error: {e}")

        demand_res = self.get_skill_demand(db=db, mode="live")
        _, emp_signals = MLDataService.get_live_employer_feedback_data(db)
        return self._service.compute_skill_evidence(demand_data=demand_res, employer_feedback_data=emp_signals)

    # =================================================================
    # 7. GENERIC SKILL RECOMMENDATIONS (LIVE_READY / BENCHMARK)
    # =================================================================
    def get_skill_recommendations(self, db=None, mode: str = "live") -> SkillRecommendationResult:
        """
        Retrieve transparent rule-based skill recommendations.
        In 'live' mode: evaluates Phase 6A boolean conditions against live evidence and live course coverage.
        In 'benchmark' mode: retrieves authoritative Phase 6A benchmark artifact.
        """
        if mode == "benchmark" or db is None:
            try:
                return self._service.get_skill_recommendations()
            except ArtifactNotFoundError as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
            except MLError as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"ML recommendation error: {e}")

        evidence_res = self.get_skill_evidence(db=db, mode="live")
        course_gap_res = self.get_course_skill_gaps(db=db, mode="live")
        return self._service.compute_skill_recommendations(evidence_data=evidence_res, course_gap_data=course_gap_res)

    # =================================================================
    # =================================================================
    # 8. ROLE-CONTEXT RECOMMENDATIONS (LIVE_READY / BENCHMARK)
    # =================================================================
    def get_role_skill_context(self, role_id: str, db=None, mode: str = "live") -> RoleSkillContextResult:
        """
        Retrieve contextual recommendations for a role.
        In 'live' mode: evaluates role requirements against live generic recommendations.
        In 'benchmark' mode: retrieves Phase 6B benchmark artifact.
        """
        if mode == "benchmark" or db is None:
            try:
                return self._service.get_role_skill_context(role_id)
            except (UnknownRoleError, InvalidInputError) as e:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
            except MLError as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        role_data = MLDataService.get_live_role_data(db, role_id)
        if not role_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Target role '{role_id}' not found in database"
            )

        generic_recs = self.get_skill_recommendations(db=db, mode="live")
        return self._service.compute_role_skill_context(role_data=role_data, generic_recommendations=generic_recs)

    # =================================================================
    # 9. STUDENT PROFILE (LIVE_READY / BENCHMARK)
    # =================================================================
    def get_student_skill_profile(self, student_id: str, db=None, mode: str = "live") -> StudentProfileResult:
        """
        Retrieve normalized canonical skill profile for a student.
        In 'live' mode: aggregates student evidence records from database.
        In 'benchmark' mode: retrieves Phase 7A benchmark artifact.
        """
        if mode == "benchmark" or db is None:
            try:
                return self._service.get_student_skill_profile(student_id)
            except (UnknownStudentError, InvalidInputError) as e:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
            except MLError as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        student_data = MLDataService.get_live_student_data(db, student_id)
        if not student_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student profile '{student_id}' not found in database"
            )

        return self._service.compute_student_skill_profile(
            student_id=student_id,
            evidence_records=student_data["evidence_records"]
        )

    # =================================================================
    # 10. STUDENT GAP (LIVE_READY / BENCHMARK)
    # =================================================================
    def get_student_skill_gap(self, student_id: str, role_id: str, db=None, mode: str = "live") -> StudentGapResult:
        """
        Retrieve student-to-target-role skill gap analysis.
        In 'live' mode: compares live student profile with live role context.
        In 'benchmark' mode: retrieves Phase 7B benchmark artifact.
        """
        if mode == "benchmark" or db is None:
            try:
                return self._service.get_student_skill_gap(student_id, role_id)
            except (UnknownStudentError, UnknownRoleError, InvalidInputError) as e:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
            except MLError as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        student_profile = self.get_student_skill_profile(student_id=student_id, db=db, mode="live")
        role_context = self.get_role_skill_context(role_id=role_id, db=db, mode="live")
        return self._service.compute_student_skill_gap(
            student_profile=student_profile,
            role_context=role_context
        )

    # =================================================================
    # 11. PERSONALIZED RECOMMENDATIONS (LIVE_READY / BENCHMARK)
    # =================================================================
    def get_personalized_recommendations(self, student_id: str, role_id: str, db=None, mode: str = "live") -> PersonalizedRecommendationResult:
        """
        Retrieve personalized skill development recommendations.
        In 'live' mode: evaluates gap against live generic recommendations.
        In 'benchmark' mode: retrieves Phase 7C benchmark artifact.
        """
        if mode == "benchmark" or db is None:
            try:
                return self._service.get_personalized_recommendations(student_id, role_id)
            except (UnknownStudentError, UnknownRoleError, InvalidInputError) as e:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
            except MLError as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        student_gap = self.get_student_skill_gap(student_id=student_id, role_id=role_id, db=db, mode="live")
        generic_recs = self.get_skill_recommendations(db=db, mode="live")
        return self._service.compute_personalized_recommendations(
            student_gap=student_gap,
            generic_recommendations=generic_recs
        )

    # =================================================================
    # 12. COURSE CANDIDATES (LIVE_READY / BENCHMARK)
    # =================================================================
    def get_course_candidates(self, student_id: str, role_id: str, db=None, mode: str = "live") -> CourseCandidateResult:
        """
        Retrieve candidate courses for a student's personalized recommendations.
        In 'live' mode: matches live courses against live personalized recommendations.
        In 'benchmark' mode: retrieves Phase 7E benchmark artifact.
        """
        if mode == "benchmark" or db is None:
            try:
                return self._service.get_course_candidates(student_id, role_id)
            except (UnknownStudentError, UnknownRoleError, InvalidInputError) as e:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
            except MLError as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        personalized_recs = self.get_personalized_recommendations(student_id=student_id, role_id=role_id, db=db, mode="live")
        courses = MLDataService.get_live_courses_data(db)
        return self._service.compute_course_candidates(
            personalized_recommendations=personalized_recs,
            courses=courses
        )

# Shared singleton instance for dependency injection
_ml_adapter_instance: Optional[MLAdapter] = None

def get_ml_adapter() -> MLAdapter:
    global _ml_adapter_instance
    if _ml_adapter_instance is None:
        _ml_adapter_instance = MLAdapter()
    return _ml_adapter_instance
