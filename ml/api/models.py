from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

# =====================================================================
# CUSTOM ML SERVICE EXCEPTIONS
# =====================================================================

class MLError(Exception):
    """Base exception for all ML service errors."""
    pass

class InvalidInputError(MLError):
    """Raised when an input parameter fails validation."""
    pass

class ArtifactNotFoundError(MLError):
    """Raised when a required pipeline artifact cannot be located."""
    pass

class SchemaValidationError(MLError):
    """Raised when an artifact or input fails schema validation."""
    pass

class UnknownSkillError(MLError):
    """Raised when a skill ID is not recognized in the canonical taxonomy."""
    pass

class UnknownStudentError(MLError):
    """Raised when a student ID is not found in the student dataset."""
    pass

class UnknownRoleError(MLError):
    """Raised when a role ID is not found in the role taxonomy/context."""
    pass

# =====================================================================
# SERVICE LAYER DATA MODELS
# =====================================================================

@dataclass
class JobProcessingResult:
    job_id: str
    title: str
    company: str
    location: str
    extracted_skills: List[Dict[str, Any]]
    total_skills_extracted: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class SkillDemandResult:
    total_jobs_analyzed: int
    total_unique_skills_demanded: int
    top_skills: List[Dict[str, Any]]
    category_demand: Dict[str, int]
    source_distribution: Dict[str, int]
    is_synthetic_artifact: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class CourseGapResult:
    total_courses_analyzed: int
    total_skills_demanded: int
    overall_taught_coverage_ratio: float
    course_gaps: List[Dict[str, Any]]
    is_synthetic_artifact: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class EmployerFeedbackResult:
    total_feedback_records: int
    detected_skills: List[Dict[str, Any]]
    course_signals: List[Dict[str, Any]]
    is_synthetic_artifact: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class SkillEvidenceResult:
    total_skills_evaluated: int
    multi_signal_skills: List[Dict[str, Any]]
    is_synthetic_artifact: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class SkillRecommendationResult:
    total_skills_evaluated: int
    recommended_skills: List[Dict[str, Any]]
    not_recommended_skills: List[Dict[str, Any]]
    is_synthetic_artifact: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class RoleSkillContextResult:
    role_id: str
    role_name: str
    contextual_recommendations: List[Dict[str, Any]]
    summary: Dict[str, int]
    is_synthetic_artifact: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class StudentProfileResult:
    student_id: str
    profile_skills: List[Dict[str, Any]]
    summary: Dict[str, int]
    is_synthetic_artifact: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class StudentGapResult:
    student_id: str
    role: Dict[str, str]
    skill_gaps: List[Dict[str, Any]]
    summary: Dict[str, int]
    is_synthetic_artifact: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class PersonalizedRecommendationResult:
    student_id: str
    role: Dict[str, str]
    skill_recommendations: List[Dict[str, Any]]
    summary: Dict[str, int]
    is_synthetic_artifact: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class CourseCandidateResult:
    student_id: str
    role: Dict[str, str]
    personalized_skill_ids: List[str]
    candidate_courses: List[Dict[str, Any]]
    uncovered_personalized_skills: List[str]
    summary: Dict[str, int]
    is_synthetic_artifact: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
