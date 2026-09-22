try:
    from fastapi import FastAPI, APIRouter, Depends, status
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:
    class APIRouter:
        def __init__(self, *args, **kwargs):
            self.routes = []
        def post(self, path, **kwargs):
            def decorator(func):
                self.routes.append(("POST", path, func))
                return func
            return decorator
        def get(self, path, **kwargs):
            def decorator(func):
                self.routes.append(("GET", path, func))
                return func
            return decorator

    class FastAPI:
        def __init__(self, *args, **kwargs):
            self.routers = []
        def include_router(self, router, **kwargs):
            self.routers.append(router)
        def add_middleware(self, *args, **kwargs):
            pass
        def get(self, path, **kwargs):
            def decorator(func):
                return func
            return decorator

    class CORSMiddleware:
        pass

    def Depends(dep):
        return dep

    class status:
        HTTP_200_OK = 200
        HTTP_201_CREATED = 201

from .config import settings
from .api import (
    jobs_router,
    employers_router,
    ml_router,
    roles_router,
    students_router,
    auth_router,
    skills_router,
    courses_router,
    course_skills_router,
    job_postings_router,
    job_skills_router,
    user_skills_router,
)

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        description="WorkNexus / SkillMesh Core Backend API with Integrated ML Engine"
    )

    # Initialize tables if using SQLite or dev database
    try:
        from .db.base import Base
        from .db.database import engine
        # Import all SQLAlchemy models to bind metadata
        from .models import users, skills, courses, course_skills, job_postings, jobSkill, refresh_tokens, user_skills
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass

    try:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "http://localhost:3000",
                "http://localhost:5173",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    except Exception:
        pass

    # Core Authentication & CRUD Routers (available at both root and /api/v1 for compatibility)
    for prefix in ["", settings.API_V1_STR]:
        app.include_router(auth_router, prefix=prefix)
        app.include_router(skills_router, prefix=prefix)
        app.include_router(courses_router, prefix=prefix)
        app.include_router(course_skills_router, prefix=prefix)
        app.include_router(job_postings_router, prefix=prefix)
        app.include_router(job_skills_router, prefix=prefix)
        app.include_router(user_skills_router, prefix=prefix)

    # ML Intelligence & WorkNexus Domain Routers
    app.include_router(jobs_router, prefix=f"{settings.API_V1_STR}/jobs", tags=["Jobs"])
    app.include_router(employers_router, prefix=f"{settings.API_V1_STR}/employers", tags=["Employers"])
    app.include_router(ml_router, prefix=f"{settings.API_V1_STR}/ml", tags=["ML Intelligence"])
    app.include_router(roles_router, prefix=f"{settings.API_V1_STR}/roles", tags=["Career Roles"])
    app.include_router(students_router, prefix=f"{settings.API_V1_STR}/students", tags=["Students"])

    @app.get("/", tags=["Root"])
    def root_endpoint():
        return {"status": "healthy", "service": "worknexus-backend", "message": "WorkNexus API"}

    @app.get("/health", tags=["Health"])
    def health_check():
        return {"status": "healthy", "service": "worknexus-backend"}

    return app


app = create_app()
