from .routes_jobs import router as jobs_router
from .routes_employers import router as employers_router
from .routes_ml import router as ml_router
from .routes_roles import router as roles_router
from .routes_students import router as students_router
from .routes_trainers import router as trainer_interventions_router  # Phase 1 — Loop D
from .auth import router as auth_router
from .skills import router as skills_router
from .courses import router as courses_router
from .course_skills import router as course_skills_router
from .job_postings import router as job_postings_router
from .job_skills import router as job_skills_router
from .user_skills import router as user_skills_router

__all__ = [
    "jobs_router",
    "employers_router",
    "ml_router",
    "roles_router",
    "students_router",
    "trainer_interventions_router",
    "auth_router",
    "skills_router",
    "courses_router",
    "course_skills_router",
    "job_postings_router",
    "job_skills_router",
    "user_skills_router",
]
