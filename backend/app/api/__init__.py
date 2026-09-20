from .routes_jobs import router as jobs_router
from .routes_employers import router as employers_router
from .routes_ml import router as ml_router
from .routes_roles import router as roles_router
from .routes_students import router as students_router

__all__ = ["jobs_router", "employers_router", "ml_router", "roles_router", "students_router"]
