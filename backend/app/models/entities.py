"""
Domain entity compatibility module.
Re-exports canonical SQLAlchemy models from app.models to eliminate duplicate model definitions.
"""
from app.models.users import User
from app.models.skills import Skill
from app.models.courses import Course
from app.models.course_skills import CourseSkill
from app.models.employers import Employer, EmployerFeedback, EmployerFeedbackSignal
from app.models.job_postings import JobPosting
from app.models.jobSkill import JobSkill
from app.models.student_roles import TargetRole, RoleSkill, StudentProfile, StudentSkillEvidence

__all__ = [
    "User",
    "Skill",
    "Course",
    "CourseSkill",
    "Employer",
    "EmployerFeedback",
    "EmployerFeedbackSignal",
    "JobPosting",
    "JobSkill",
    "TargetRole",
    "RoleSkill",
    "StudentProfile",
    "StudentSkillEvidence",
]
