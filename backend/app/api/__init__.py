from app.api.auth import router as auth_router
from app.api.skills import router as skills_router
from app.api.courses import router as courses_router
from app.api.user_skills import router as user_skills_router
from app.api.course_skills import router as course_skills_router

__all__ = [
    "auth_router",
    "skills_router",
    "courses_router",
    "user_skills_router",
    "course_skills_router",
]
