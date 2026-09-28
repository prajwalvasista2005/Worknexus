from typing import Dict, List, Any, Optional, Type, Generator
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings
from app.db.base import Base

# Configure connection parameters based on dialect
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    Standard FastAPI dependency yielding a managed SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# Legacy Test Mock Support (Preserved exclusively for isolated unit tests)
# =============================================================================

class MockDatabaseSession:
    """
    Lightweight in-memory test session fixture preserved for isolated unit testing.
    """

    def __init__(self):
        self.users: Dict[int, Any] = {}
        self.skills: Dict[str, Any] = {}
        self.courses: Dict[int, Any] = {}
        self.course_skills: List[Any] = []
        self.employers: Dict[int, Any] = {}
        self.job_postings: Dict[int, Any] = {}
        self.job_skills: List[Any] = []
        self.employer_feedback: Dict[int, Any] = {}
        self.employer_feedback_signals: List[Any] = []

        # Phase 10 Entities
        self.target_roles: Dict[str, Any] = {}
        self.role_skills: List[Any] = []
        self.student_profiles: Dict[int, Any] = {}
        self.student_skill_evidence: List[Any] = []

        self._user_id_counter = 1
        self._employer_id_counter = 1
        self._job_id_counter = 1
        self._fb_id_counter = 1
        self._signal_id_counter = 1
        self._job_skill_id_counter = 1
        self._role_skill_id_counter = 1
        self._student_profile_id_counter = 1
        self._evidence_id_counter = 1

    def add(self, entity: Any):
        name = type(entity).__name__
        if name == "User":
            if not getattr(entity, "id", None):
                entity.id = self._user_id_counter
                self._user_id_counter += 1
            self.users[entity.id] = entity
        elif name == "Skill":
            sk_id = getattr(entity, "skill_id", getattr(entity, "id", None))
            self.skills[str(sk_id)] = entity
        elif name == "Course":
            self.courses[entity.id] = entity
        elif name == "CourseSkill":
            self.course_skills.append(entity)
        elif name == "Employer":
            if not getattr(entity, "id", None):
                entity.id = self._employer_id_counter
                self._employer_id_counter += 1
            self.employers[entity.id] = entity
        elif name == "JobPosting":
            if not getattr(entity, "id", None):
                entity.id = self._job_id_counter
                self._job_id_counter += 1
            self.job_postings[entity.id] = entity
        elif name == "JobSkill":
            if not getattr(entity, "id", None):
                entity.id = self._job_skill_id_counter
                self._job_skill_id_counter += 1
            self.job_skills.append(entity)
        elif name == "EmployerFeedback":
            if not getattr(entity, "id", None):
                entity.id = self._fb_id_counter
                self._fb_id_counter += 1
            self.employer_feedback[entity.id] = entity
        elif name == "EmployerFeedbackSignal":
            if not getattr(entity, "id", None):
                entity.id = self._signal_id_counter
                self._signal_id_counter += 1
            self.employer_feedback_signals.append(entity)
        elif name == "TargetRole":
            self.target_roles[entity.id] = entity
        elif name == "RoleSkill":
            if not getattr(entity, "id", None):
                entity.id = self._role_skill_id_counter
                self._role_skill_id_counter += 1
            self.role_skills.append(entity)
        elif name == "StudentProfile":
            if not getattr(entity, "id", None):
                entity.id = self._student_profile_id_counter
                self._student_profile_id_counter += 1
            self.student_profiles[entity.id] = entity
        elif name == "StudentSkillEvidence":
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
        name = getattr(self.entity_class, "__name__", str(self.entity_class))
        if name == "Employer":
            items = list(self.session.employers.values())
        elif name == "JobPosting":
            items = list(self.session.job_postings.values())
        elif name == "JobSkill":
            items = list(self.session.job_skills)
        elif name == "EmployerFeedback":
            items = list(self.session.employer_feedback.values())
        elif name == "EmployerFeedbackSignal":
            items = list(self.session.employer_feedback_signals)
        elif name == "Skill":
            items = list(self.session.skills.values())
        elif name == "Course":
            items = list(self.session.courses.values())
        elif name == "CourseSkill":
            items = list(self.session.course_skills)
        elif name == "User":
            items = list(self.session.users.values())
        elif name == "TargetRole":
            items = list(self.session.target_roles.values())
        elif name == "RoleSkill":
            items = list(self.session.role_skills)
        elif name == "StudentProfile":
            items = list(self.session.student_profiles.values())
        elif name == "StudentSkillEvidence":
            items = list(self.session.student_skill_evidence)
        else:
            items = []

        for f in self._filters:
            if callable(f):
                items = [item for item in items if f(item)]
        return items


_global_session = MockDatabaseSession()
