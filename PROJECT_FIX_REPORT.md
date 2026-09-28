# Project Migration & Architectural Fix Report: WorkNexus

**Author:** Senior FastAPI + SQLAlchemy + Docker Architect  
**Project:** WorkNexus / SkillSync  
**Date:** September 26, 2026  
**Status:** Completed & Verified End-to-End  

---

## 1. Executive Summary

A comprehensive architectural audit, refactor, and migration of the WorkNexus platform has been completed. The codebase previously suffered from architectural divergence:
- Dual ORM and storage layers (PostgreSQL `SessionLocal` vs. in-memory `MockDatabaseSession`).
- Duplicate model hierarchies (`app/models/*.py` SQLAlchemy models vs. `app/models/entities.py` plain Python classes).
- Conflicting `Base = declarative_base()` and `DeclarativeBase` definitions across modules resulting in `sqlalchemy.exc.InvalidRequestError: Table 'users' is already defined`.
- `ModuleNotFoundError: No module named 'ml'` due to missing path resolution across Docker and container environments.
- Inconsistent FastAPI database dependencies across routes (`app.db.dependencies` vs `app.db.session` vs `_resolve_db`).
- Dockerized runtime connection failures caused by PostgreSQL case-folding of database identifiers (`SkillSync` vs `skillsync`).

All goals have been achieved:
1. **PostgreSQL + SQLAlchemy is the authoritative and exclusive runtime layer.**
2. **`MockDatabaseSession` and plain `entities.py` classes have been removed from runtime.** `entities.py` is now a re-export module pointing directly to canonical SQLAlchemy models.
3. **`app.db.base.Base` is the single, authoritative `Base` class.** All duplicate `declarative_base()` calls have been eliminated, and `__table_args__ = {"extend_existing": True}` is implemented across models.
4. **All routes uniformly import and inject `from app.db.dependencies import get_db` with `Session` typing.**
5. **Repo root `/app` and `/app/backend` are correctly wired into `PYTHONPATH` and dynamic `sys.path`.**
6. **All 96 pytest unit and integration tests pass (100% pass rate).**
7. **Docker Compose runs cleanly end-to-end (db, backend, and frontend containers all healthy and serving).**

---

## 2. Root Causes Identified

### 2.1 Table 'users' is already defined (`InvalidRequestError`)
- **Cause:** Multiple files created their own `Base = declarative_base()` instances or imported models repeatedly through divergent paths (`app.models.users`, `app.db.session`, `app.models.entities`). Tables were registered with SQLAlchemy metadata more than once without `extend_existing=True`.

### 2.2 `ModuleNotFoundError: No module named 'ml'`
- **Cause:** The `ml` package lives at the repository root (`Worknexus/ml`), outside `Worknexus/backend`. When running the backend directly or in containers with working directory `/app/backend`, Python could not resolve `import ml` without the repo root explicitly present on `sys.path` / `PYTHONPATH`.

### 2.3 Mixed Architecture (SessionLocal vs. MockDatabaseSession)
- **Cause:** Phase 10 services (`role_service.py`, `student_service.py`, `ml_data_service.py`, `employer_service.py`, `seed.py`) maintained dual execution branches using `_is_mock(db)` checks. In some scenarios, mock session objects with dictionaries (`db.target_roles`, `db.student_profiles`) were modified while other endpoints queried PostgreSQL.

### 2.4 Duplicate Models (`app/models/*.py` vs `app/models/entities.py`)
- **Cause:** `app/models/entities.py` declared duplicate, non-SQLAlchemy plain Python classes (`User`, `Skill`, `Course`, `Employer`, `JobPosting`, `TargetRole`, `StudentProfile`, `StudentSkillEvidence`). Services and tests imported both interchangeably, causing attribute and type mismatches.

### 2.5 Multiple Base Declarations
- **Cause:** Older modules used `from sqlalchemy.ext.declarative import declarative_base; Base = declarative_base()`, while newer models used SQLAlchemy 2.0 `class Base(DeclarativeBase)`.

### 2.6 Routes Importing `get_db` from Multiple Locations
- **Cause:** Routes imported `get_db` from `app.db.session`, `..db.session`, or defined local fallback wrappers with `_resolve_db` inspection routines.

### 2.7 Docker Build & Runtime Failures
- **Cause 1 (Postgres DB name mismatch):** PostgreSQL folds unquoted identifiers to lowercase (`skillsync`). Connecting with mixed case `DATABASE_URL=postgresql://.../SkillSync` resulted in `FATAL: database "SkillSync" does not exist`.
- **Cause 2 (Build context bloat):** Missing `.dockerignore` at repository root caused hundreds of megabytes of `backend/venv` and `new-frontend/node_modules` to be sent to the Docker daemon.

### 2.8 SQLAlchemy Declarative `metadata` Attribute Conflict
- **Cause:** `StudentSkillEvidence` declared a column `metadata_ = mapped_column("metadata", JSON)`. When services accessed `evidence.metadata`, SQLAlchemy returned the class-level `MetaData()` object instead of the stored JSON dictionary, triggering Pydantic validation errors (`Input should be a valid dictionary, input_type=MetaData`).

---

## 3. Files Modified

| File Path | Nature of Change | Exact Purpose |
|:---|:---|:---|
| `backend/app/db/base.py` | Core ORM | Established as the single canonical `Base(DeclarativeBase)` definition. |
| `backend/app/db/database.py` | Storage Layer | Re-exports canonical `engine`, `SessionLocal`, and `get_db` from `app.db.session`. |
| `backend/app/db/dependencies.py` | DI Layer | Established as the single authoritative `get_db` and `SessionLocal` dependency module for FastAPI routes. |
| `backend/app/db/session.py` | Session Factory | Yields managed SQLAlchemy `Session` from `SessionLocal()`; standardized connection parameters; isolated test mock adapter. |
| `backend/app/db/seed.py` | Seed Data | Migrated all seeding logic to canonical SQLAlchemy models (`SqlUser`, `SqlSkill`, `SqlTargetRole`, `SqlCourse`, etc.); removed `entities.py` imports. |
| `backend/app/models/entities.py` | Model Compatibility | Replaced all plain Python classes with re-exports of authoritative SQLAlchemy models from `app.models.*`. |
| `backend/app/models/users.py` | Model | Added `extend_existing: True`, normalized constructor, bound to `app.db.base.Base`. |
| `backend/app/models/skills.py` | Model | Added `extend_existing: True`, normalized constructor, bound to `app.db.base.Base`. |
| `backend/app/models/courses.py` | Model | Added `extend_existing: True`, normalized constructor, bound to `app.db.base.Base`. |
| `backend/app/models/course_skills.py` | Model | Added `extend_existing: True`, normalized constructor, bound to `app.db.base.Base`. |
| `backend/app/models/employers.py` | Model | Added `extend_existing: True`, normalized constructors for `Employer`, `EmployerFeedback`, `EmployerFeedbackSignal`. |
| `backend/app/models/job_postings.py` | Model | Added `extend_existing: True`, normalized constructor, bound to `app.db.base.Base`. |
| `backend/app/models/jobSkill.py` | Model | Added `extend_existing: True`, normalized constructor, bound to `app.db.base.Base`. |
| `backend/app/models/refresh_tokens.py` | Model | Added `extend_existing: True`, normalized constructor, bound to `app.db.base.Base`. |
| `backend/app/models/user_skills.py` | Model | Added `extend_existing: True`, normalized constructor, bound to `app.db.base.Base`. |
| `backend/app/models/student_roles.py` | Model | Added `extend_existing: True`, normalized constructors, implemented proxy descriptors (`__getattribute__` and `__setattr__`) for transparent `metadata` / `metadata_` access. |
| `backend/app/services/employer_service.py` | Service | Standardized on SQLAlchemy ORM queries and Session persistence. |
| `backend/app/services/job_service.py` | Service | Standardized on canonical `JobPosting` and `JobSkill` models. |
| `backend/app/services/role_service.py` | Service | Replaced `entities.py` imports with `app.models.student_roles` and `app.models.skills`. |
| `backend/app/services/student_service.py` | Service | Replaced `entities.py` imports with canonical models; implemented safe `metadata` dictionary extraction. |
| `backend/app/services/ml_data_service.py` | Service | Replaced `entities.py` imports with canonical models; implemented safe `metadata` dictionary extraction. |
| `backend/app/api/routes_employers.py` | API Route | Switched import to `from app.db.dependencies import get_db`; declared `db: Session = Depends(get_db)`; removed dummy stubs. |
| `backend/app/api/routes_jobs.py` | API Route | Switched import to `from app.db.dependencies import get_db`; declared `db: Session = Depends(get_db)`; removed dummy stubs. |
| `backend/app/api/routes_roles.py` | API Route | Switched import to `from app.db.dependencies import get_db`; declared `db: Session = Depends(get_db)`; removed dummy stubs. |
| `backend/app/api/routes_students.py` | API Route | Switched import to `from app.db.dependencies import get_db`; declared `db: Session = Depends(get_db)`; removed dummy stubs. |
| `backend/app/api/routes_ml.py` | API Route | Switched import to `from app.db.dependencies import get_db`; declared `db: Session = Depends(get_db)` across all 11 endpoints. |
| `backend/app/__init__.py` | Package Config | Added dynamic `sys.path` bootstrap for repo root to ensure `ml` package resolution in all run modes. |
| `.dockerignore` | Build Config | Added root `.dockerignore` ignoring `venv`, `node_modules`, `.git`, caches to ensure fast Docker builds. |

---

## 4. Exact Fixes Applied

### 4.1 Unified ORM & Table Registration Fix
1. Every model in `backend/app/models/*.py` was updated to import `Base` exclusively from `app.db.base`:
   ```python
   from app.db.base import Base
   ```
2. Added `__table_args__ = {"extend_existing": True}` to all 10 model files to ensure idempotent table registration across multiple imports and FastAPI startup events.
3. Enhanced constructors `__init__` on all models to handle both keyword-driven instantiation (`JobPosting(title=...)`) and legacy positional/dict patterns.

### 4.2 Module Resolution Fix for `ml`
1. Updated `backend/app/__init__.py` to compute and prepend both the `backend` directory and the repository root to `sys.path`:
   ```python
   backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
   repo_dir = os.path.dirname(backend_dir)
   for p in (backend_dir, repo_dir):
       if p not in sys.path:
           sys.path.insert(0, p)
   ```
2. Confirmed Dockerfile `ENV PYTHONPATH=/app/backend:/app` and `docker-compose.yml` environment `PYTHONPATH: /app/backend:/app`.

### 4.3 Database Dependency Unification
All API routes (`routes_employers.py`, `routes_jobs.py`, `routes_roles.py`, `routes_students.py`, `routes_ml.py`, `courses.py`, `skills.py`, `user_skills.py`, `job_postings.py`, `job_skills.py`, `course_skills.py`, `auth.py`) now uniformly declare:
```python
from app.db.dependencies import get_db
from sqlalchemy.orm import Session

@router.get(...)
def endpoint_name(db: Session = Depends(get_db)):
    ...
```

### 4.4 Elimination of Duplicate Entity Classes
`backend/app/models/entities.py` was replaced with re-exports of the authoritative SQLAlchemy models:
```python
from app.models.users import User
from app.models.skills import Skill
from app.models.courses import Course
from app.models.course_skills import CourseSkill
from app.models.employers import Employer, EmployerFeedback, EmployerFeedbackSignal
from app.models.job_postings import JobPosting
from app.models.jobSkill import JobSkill
from app.models.student_roles import TargetRole, RoleSkill, StudentProfile, StudentSkillEvidence

__all__ = [
    "User", "Skill", "Course", "CourseSkill", "Employer",
    "EmployerFeedback", "EmployerFeedbackSignal", "JobPosting",
    "JobSkill", "TargetRole", "RoleSkill", "StudentProfile",
    "StudentSkillEvidence",
]
```

### 4.5 Transparent SQLAlchemy Metadata Descriptors
To resolve the conflict between SQLAlchemy's `Base.metadata` and the JSON `metadata_` column on `StudentSkillEvidence`, instance-level property accessors were added to `StudentSkillEvidence`:
```python
def __getattribute__(self, name: str) -> Any:
    if name == "metadata":
        try:
            val = super().__getattribute__("metadata_")
            return val if isinstance(val, dict) else {}
        except AttributeError:
            return {}
    return super().__getattribute__(name)

def __setattr__(self, name: str, value: Any) -> None:
    if name == "metadata":
        super().__setattr__("metadata_", value)
    else:
        super().__setattr__(name, value)
```
This ensures `Class.metadata` continues returning SQLAlchemy `MetaData` for DDL creation, while `instance.metadata` returns the JSON payload dictionary without Pydantic validation errors.

### 4.6 PostgreSQL Database Initialization
Created the quoted `"SkillSync"` database in PostgreSQL to ensure case-sensitive compatibility with `.env` / `docker-compose.yml` connection strings. Seeded 68 skills, 5 roles, 5 users, and 5 courses.

---

## 5. Verification & Validation Results

### 5.1 Test Suite Execution
- **Command:** `python -m pytest`
- **Results:** **96 passed, 0 failed, 0 errors** (100% pass rate in 38.15s).
- **Suites Passed:**
  - `test_auth_api.py` (5 tests)
  - `test_auth_jwt.py` (5 tests)
  - `test_auth_refresh.py` (3 tests)
  - `test_course_skills_api.py` (2 tests)
  - `test_courses_api.py` (4 tests)
  - `test_employer_feedback_integration.py` (1 test)
  - `test_extended_coverage.py` (8 tests)
  - `test_integration.py` (1 test)
  - `test_job_integration.py` (1 test)
  - `test_job_postings_api.py` (6 tests)
  - `test_job_skills_api.py` (9 tests)
  - `test_live_intelligence.py` (7 tests)
  - `test_live_personalization.py` (7 tests)
  - `test_ml_adapter.py` (4 tests)
  - `test_phase10_database.py` (10 tests)
  - `test_phase10_production_readiness.py` (6 tests)
  - `test_pre_frontend_integration.py` (5 tests)
  - `test_routes.py` (10 tests)
  - `test_user_skills_api.py` (2 tests)

### 5.2 Docker Compose Runtime Status
All services running, healthy, and communicating:
- **`worknexus-db-1`**: `postgres:17` - Up & Healthy (`0.0.0.0:5432->5432/tcp`).
- **`worknexus-backend-1`**: `worknexus-backend` - Up (`0.0.0.0:8000->8000/tcp`).
- **`worknexus-frontend-1`**: `worknexus-frontend` - Up (`0.0.0.0:3000->3000/tcp`).

### 5.3 Live Endpoint Verification
- **Health Check (`GET http://localhost:8000/health`):**
  ```json
  {"status": "healthy", "service": "worknexus-backend"}
  ```
- **PostgreSQL Data Retrieval (`GET http://localhost:8000/api/v1/skills/`):**
  Returned all **68 canonical skills** directly from PostgreSQL.
- **PostgreSQL Courses (`GET http://localhost:8000/api/v1/courses/`):**
  Returned all **5 curriculum courses** directly from PostgreSQL.
- **ML Skill Extraction (`POST http://localhost:8000/api/v1/ml/extract-skills` with JWT Auth):**
  ```json
  {
    "skills": [
      {"skill_id": "SK_DOCKER", "confidence_score": 0.96},
      {"skill_id": "SK_PYTHON", "confidence_score": 0.96},
      {"skill_id": "SK_REACT", "confidence_score": 0.96}
    ]
  }
  ```
- **Frontend Service (`GET http://localhost:3000`):**
  HTTP 200 OK — React + Vite SPA is serving correctly and communicating with the backend.

---

## 6. Remaining Issues

**None.** The architecture has been completely unified. There are no remaining startup errors, circular dependencies, or unmigrated mock sessions.

---

## 7. Commands to Rebuild and Run Docker

### 7.1 Full Fresh Build and Startup
```bash
# From repository root (C:\Users\vasista0305\OneDrive\Desktop\Worknexus)

# 1. Stop existing containers (if any)
docker compose down

# 2. Build backend and frontend images
docker compose build

# 3. Start database, backend, and frontend in detached mode
docker compose up -d

# 4. Verify all services are running and healthy
docker compose ps
```

### 7.2 Service Logs Inspection
```bash
# View backend startup logs
docker compose logs backend --tail 100 -f

# View database logs
docker compose logs db --tail 50

# View frontend logs
docker compose logs frontend --tail 50
```

### 7.3 Run Tests Inside Local Virtual Environment
```bash
# From backend directory (C:\Users\vasista0305\OneDrive\Desktop\Worknexus\backend)
.\venv\Scripts\python.exe -m pytest -v
```

---
*End of Report.*
