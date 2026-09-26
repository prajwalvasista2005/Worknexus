from fastapi import FastAPI, APIRouter, Depends, status
from fastapi.middleware.cors import CORSMiddleware

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

    # Initialize tables and seed canonical taxonomy
    try:
        from .db.base import Base
        from .db.session import engine, SessionLocal
        # Import all SQLAlchemy models to bind metadata
        from .models import users, skills, courses, course_skills, job_postings, jobSkill, refresh_tokens, user_skills, student_roles, employers
        Base.metadata.create_all(bind=engine)

        # Ensure user_id column exists on employers table for existing databases
        from sqlalchemy import text
        with engine.connect() as conn:
            try:
                if engine.dialect.name == "sqlite":
                    cols = [row[1] for row in conn.execute(text("PRAGMA table_info(employers)")).fetchall()]
                    if cols and "user_id" not in cols:
                        conn.execute(text("ALTER TABLE employers ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE"))
                        conn.commit()
                elif engine.dialect.name == "postgresql":
                    cols = [row[0] for row in conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'employers'")).fetchall()]
                    if cols and "user_id" not in cols:
                        conn.execute(text("ALTER TABLE employers ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE"))
                        conn.commit()
            except Exception:
                pass

        # Idempotent seed check for production / dev PostgreSQL database
        from .db.seed import seed_all
        with SessionLocal() as db_session:
            seed_all(db_session)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Database initialization warning: {e}")

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
