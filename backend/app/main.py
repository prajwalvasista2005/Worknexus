import logging
from contextlib import asynccontextmanager
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup audit and self-healing validation for employer profiles
    try:
        from .db.session import SessionLocal
        from .services.employer_service import EmployerService
        with SessionLocal() as db_session:
            EmployerService.verify_employer_profiles(db_session)
            # Idempotent seed check for production / dev PostgreSQL database
            from .db.seed import seed_all
            seed_all(db_session)
    except Exception as e:
        logging.getLogger(__name__).warning(f"Database startup check warning: {e}")

    yield

    # Graceful shutdown: cleanly dispose of SQLAlchemy engine connections
    try:
        from .db.session import engine
        engine.dispose()
        logging.getLogger(__name__).info("Database engine connection pool cleanly disposed.")
    except Exception as e:
        logging.getLogger(__name__).warning(f"Error disposing database engine on shutdown: {e}")


def create_app() -> FastAPI:
    # 1. Enforce production cryptographic key security invariants
    settings.validate_production_security()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        description="WorkNexus / SkillMesh Core Backend API with Integrated ML Engine",
        lifespan=lifespan,
    )

    from .middleware import (
        RequestCorrelationMiddleware,
        RequestIdFilter,
        SensitiveDataFilter,
        get_request_id,
        RateLimitMiddleware,
        SecurityHeadersMiddleware,
    )

    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestCorrelationMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Configure structured logging filters
    req_filter = RequestIdFilter()
    sec_filter = SensitiveDataFilter()
    logging.getLogger().addFilter(req_filter)
    logging.getLogger().addFilter(sec_filter)

    # Global Exception Handlers
    from fastapi.responses import JSONResponse
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException

    logger = logging.getLogger("worknexus")
    logger.addFilter(req_filter)
    logger.addFilter(sec_filter)

    def _cors_headers(request):
        origin = request.headers.get("origin")
        allowed = origin if (origin and (origin in settings.CORS_ORIGINS or "*" in settings.CORS_ORIGINS)) else (origin or "*")
        headers = {
            "Access-Control-Allow-Origin": allowed,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        }
        rid = get_request_id()
        if rid:
            headers["X-Request-ID"] = rid
        return headers

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=_cors_headers(request),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()},
            headers=_cors_headers(request),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
        detail_msg = str(exc) if exc and str(exc) else "Internal server error. Please try again later."
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": detail_msg},
            headers=_cors_headers(request),
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
    @app.get(f"{settings.API_V1_STR}/health", tags=["Health"], include_in_schema=False)
    def health_check():
        return {"status": "healthy", "service": "worknexus-backend"}

    return app


app = create_app()
