from typing import Dict, List, Any, Optional, Type
from datetime import datetime, timezone
from ..models.entities import (
    User, Skill, Course, CourseSkill, Employer, JobPosting, JobSkill,
    EmployerFeedback, EmployerFeedbackSignal,
    TargetRole, RoleSkill, StudentProfile, StudentSkillEvidence
)

try:
    from sqlalchemy.orm import declarative_base, sessionmaker
    from sqlalchemy import create_engine
    from ..config import settings
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
except Exception:
    class _MockMetadata:
        def create_all(self, bind=None):
            pass
    class _MockBase:
        metadata = _MockMetadata()
    Base = _MockBase
    engine = None
    SessionLocal = None

class MockDatabaseSession:
    """
    Lightweight, deterministic session repository compatible with standard SQLAlchemy query patterns.
    """

    def __init__(self):
        self.users: Dict[int, User] = {}
        self.skills: Dict[str, Skill] = {}
        self.courses: Dict[int, Course] = {}
        self.course_skills: List[CourseSkill] = []
        self.employers: Dict[int, Employer] = {}
        self.job_postings: Dict[int, JobPosting] = {}
        self.job_skills: List[JobSkill] = []
        self.employer_feedback: Dict[int, EmployerFeedback] = {}
        self.employer_feedback_signals: List[EmployerFeedbackSignal] = []

        # Phase 10 Entities
        self.target_roles: Dict[str, TargetRole] = {}
        self.role_skills: List[RoleSkill] = []
        self.student_profiles: Dict[int, StudentProfile] = {}
        self.student_skill_evidence: List[StudentSkillEvidence] = []

        self._job_id_counter = 1
        self._fb_id_counter = 1
        self._signal_id_counter = 1
        self._job_skill_id_counter = 1
        self._role_skill_id_counter = 1
        self._student_profile_id_counter = 1
        self._evidence_id_counter = 1

    def add(self, entity: Any):
        if isinstance(entity, User):
            self.users[entity.id] = entity
        elif isinstance(entity, Skill):
            self.skills[entity.id] = entity
        elif isinstance(entity, Course):
            self.courses[entity.id] = entity
        elif isinstance(entity, CourseSkill):
            self.course_skills.append(entity)
        elif isinstance(entity, Employer):
            self.employers[entity.id] = entity
        elif isinstance(entity, JobPosting):
            if not getattr(entity, "id", None):
                entity.id = self._job_id_counter
                self._job_id_counter += 1
            self.job_postings[entity.id] = entity
        elif isinstance(entity, JobSkill):
            if not getattr(entity, "id", None):
                entity.id = self._job_skill_id_counter
                self._job_skill_id_counter += 1
            self.job_skills.append(entity)
        elif isinstance(entity, EmployerFeedback):
            if not getattr(entity, "id", None):
                entity.id = self._fb_id_counter
                self._fb_id_counter += 1
            self.employer_feedback[entity.id] = entity
        elif isinstance(entity, EmployerFeedbackSignal):
            if not getattr(entity, "id", None):
                entity.id = self._signal_id_counter
                self._signal_id_counter += 1
            self.employer_feedback_signals.append(entity)
        elif isinstance(entity, TargetRole):
            self.target_roles[entity.id] = entity
        elif isinstance(entity, RoleSkill):
            if not getattr(entity, "id", None):
                entity.id = self._role_skill_id_counter
                self._role_skill_id_counter += 1
            self.role_skills.append(entity)
        elif isinstance(entity, StudentProfile):
            if not getattr(entity, "id", None):
                entity.id = self._student_profile_id_counter
                self._student_profile_id_counter += 1
            self.student_profiles[entity.id] = entity
        elif isinstance(entity, StudentSkillEvidence):
            if not getattr(entity, "id", None):
                entity.id = self._evidence_id_counter
                self._evidence_id_counter += 1
            self.student_skill_evidence.append(entity)

    def flush(self):
        pass

    def commit(self):
        pass

    def refresh(self, entity: Any):
        pass

    def close(self):
        pass

    def query(self, entity_class: Type):
        return QueryBuilder(self, entity_class)

class QueryBuilder:
    def __init__(self, session: MockDatabaseSession, entity_class: Type):
        self.session = session
        self.entity_class = entity_class
        self._filters = []

    def filter(self, *expressions):
        for expr in expressions:
            self._filters.append(expr)
        return self

    def first(self) -> Optional[Any]:
        items = self.all()
        return items[0] if items else None

    def all(self) -> List[Any]:
        if self.entity_class == Employer:
            items = list(self.session.employers.values())
        elif self.entity_class == JobPosting:
            items = list(self.session.job_postings.values())
        elif self.entity_class == JobSkill:
            items = list(self.session.job_skills)
        elif self.entity_class == EmployerFeedback:
            items = list(self.session.employer_feedback.values())
        elif self.entity_class == EmployerFeedbackSignal:
            items = list(self.session.employer_feedback_signals)
        elif self.entity_class == Skill:
            items = list(self.session.skills.values())
        elif self.entity_class == Course:
            items = list(self.session.courses.values())
        elif self.entity_class == CourseSkill:
            items = list(self.session.course_skills)
        elif self.entity_class == User:
            items = list(self.session.users.values())
        elif self.entity_class == TargetRole:
            items = list(self.session.target_roles.values())
        elif self.entity_class == RoleSkill:
            items = list(self.session.role_skills)
        elif self.entity_class == StudentProfile:
            items = list(self.session.student_profiles.values())
        elif self.entity_class == StudentSkillEvidence:
            items = list(self.session.student_skill_evidence)
        else:
            items = []

        for f in self._filters:
            if callable(f):
                items = [item for item in items if f(item)]
        return items

_global_session = MockDatabaseSession()

try:
    from .seed import seed_all
    seed_all(_global_session)
except Exception:
    pass

def get_db():
    yield _global_session
