from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

class User:
    def __init__(self, id: int, email: str, role: str = "Student", is_active: bool = True):
        self.id = id
        self.email = email
        self.role = role
        self.is_active = is_active

class Skill:
    def __init__(self, id: str, name: str, category: str, version: int = 1):
        self.id = id
        self.name = name
        self.category = category
        self.version = version

class Course:
    def __init__(self, id: int, name: str, role: Optional[str] = None, duration_hours: int = 40):
        self.id = id
        self.name = name
        self.role = role
        self.duration_hours = duration_hours

class CourseSkill:
    def __init__(self, course_id: int, skill_id: str, coverage_pct: float = 100.0):
        self.course_id = course_id
        self.skill_id = skill_id
        self.coverage_pct = coverage_pct

class Employer:
    def __init__(self, id: int, company_name: str, trust_weight: float = 1.0):
        self.id = id
        self.company_name = company_name
        self.trust_weight = trust_weight

class JobPosting:
    def __init__(self, id: int, title: str, company: str, location: str, description: str, employer_id: Optional[int] = None, created_at: Optional[datetime] = None):
        self.id = id
        self.title = title
        self.company = company
        self.location = location
        self.description = description
        self.employer_id = employer_id
        self.created_at = created_at or datetime.now(timezone.utc)
        self.skills: List['JobSkill'] = []

class JobSkill:
    def __init__(self, id: int, job_id: int, skill_id: str, confidence_score: float):
        self.id = id
        self.job_id = job_id
        self.skill_id = skill_id
        self.confidence_score = confidence_score

class EmployerFeedback:
    def __init__(self, id: int, employer_id: int, comments: str, course_id: Optional[int] = None, rating: Optional[int] = None, created_at: Optional[datetime] = None):
        self.id = id
        self.employer_id = employer_id
        self.course_id = course_id
        self.comments = comments
        self.rating = rating
        self.created_at = created_at or datetime.now(timezone.utc)
        self.signals: List['EmployerFeedbackSignal'] = []

class EmployerFeedbackSignal:
    def __init__(self, id: int, feedback_id: int, skill_id: str, confidence_score: float, trust_weight: float, weighted_signal: float):
        self.id = id
        self.feedback_id = feedback_id
        self.skill_id = skill_id
        self.confidence_score = confidence_score
        self.trust_weight = trust_weight
        self.weighted_signal = weighted_signal

# =====================================================================
# PHASE 10: CAREER ROLE & STUDENT PROFILE DOMAIN ENTITIES
# =====================================================================

class TargetRole:
    def __init__(
        self,
        id: str,
        name: str,
        description: Optional[str] = None,
        is_active: bool = True,
        created_at: Optional[datetime] = None
    ):
        self.id = id  # e.g., "ROLE_DATA_ENGINEER", "ROLE_FULL_STACK_DEV"
        self.name = name
        self.description = description
        self.is_active = is_active
        self.created_at = created_at or datetime.now(timezone.utc)
        self.role_skills: List['RoleSkill'] = []

class RoleSkill:
    def __init__(
        self,
        id: Optional[int],
        role_id: str,
        skill_id: str,
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.role_id = role_id
        self.skill_id = skill_id
        self.created_at = created_at or datetime.now(timezone.utc)

class StudentProfile:
    def __init__(
        self,
        id: int,
        user_id: int,
        target_role_id: Optional[str] = None,
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.user_id = user_id
        self.target_role_id = target_role_id
        self.created_at = created_at or datetime.now(timezone.utc)
        self.skills_evidence: List['StudentSkillEvidence'] = []

class StudentSkillEvidence:
    VALID_EVIDENCE_TYPES = {
        "self_reported",
        "course_completed",
        "project",
        "certification",
        "assessment"
    }

    VALID_STRENGTH_CATEGORIES = {
        "basic",
        "intermediate",
        "advanced"
    }

    def __init__(
        self,
        id: Optional[int],
        student_profile_id: int,
        skill_id: str,
        evidence_type: str,
        strength: str,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None
    ):
        if evidence_type not in self.VALID_EVIDENCE_TYPES:
            raise ValueError(f"Invalid evidence_type '{evidence_type}'. Must be one of: {sorted(list(self.VALID_EVIDENCE_TYPES))}")
        if strength not in self.VALID_STRENGTH_CATEGORIES:
            raise ValueError(f"Invalid strength category '{strength}'. Must be one of: {sorted(list(self.VALID_STRENGTH_CATEGORIES))}")

        self.id = id
        self.student_profile_id = student_profile_id
        self.skill_id = skill_id
        self.evidence_type = evidence_type
        self.strength = strength
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.now(timezone.utc)
