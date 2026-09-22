# WorkNexus Architecture Audit Report

**Date**: September 22, 2026  
**Auditor**: Senior Staff Software Architect, Security Reviewer & ML Systems Engineer  
**Scope**: Full-Stack Architecture Audit (Frontend ↔ Backend ↔ ML Engine ↔ Database)  
**Status**: AUDITED & REMEDIATION PLAN INITIATED  

---

## 1. Executive Summary

WorkNexus is designed as a labour market intelligence and curriculum alignment platform with strict separation of concerns across four key tiers:
1. **Frontend**: Pure Presentation Tier (React 19 + TypeScript + Vite + Tailwind CSS)
2. **Backend**: Application, Persistence, Authentication, and RBAC Tier (FastAPI + SQLAlchemy 2.0 + PostgreSQL/SQLite + Pydantic v2)
3. **ML Adapter**: Anti-Corruption and Translation Layer (`MLAdapter` in `backend/app/services/ml_adapter.py`)
4. **ML Engine**: In-Process Deterministic Intelligence Package (`ml/api/service.py`)

This audit evaluated compliance against the specified architecture rules, detected critical boundary breaches, identified dead/legacy artifacts, and formulated actionable remediations.

---

## 2. Tier Boundary & Integration Compliance Matrix

| Architecture Rule | Verification Method | Status | Findings / Violations |
|---|---|---|---|
| **Architecture matches documentation** | Tree & Router Analysis | ⚠️ **PARTIAL** | Backend routes split into two groups (`app/api/` CRUD vs `routes_*.py`). Core auth & course routes omitted from `main.py`. |
| **Backend → ML follows MLAdapter** | Static import analysis | ✅ **PASS** | `backend/app/services/ml_adapter.py` is the single bridge. Zero route imports `ml.*`. |
| **No route imports ML internals** | Grep `from ml` in `backend/app/api` | ✅ **PASS** | Verified 0 occurrences. |
| **No ML module accesses DB** | Grep `db`, `sessionmaker` in `ml/` | ✅ **PASS** | Verified 0 occurrences. ML is 100% database-free and stateless. |
| **No ML module imports FastAPI** | Grep `fastapi` in `ml/` | ✅ **PASS** | Verified 0 occurrences in production ML code. |
| **No ML module imports SQLAlchemy** | Grep `sqlalchemy` in `ml/` | ✅ **PASS** | Verified 0 occurrences. |
| **No frontend code bypasses backend** | Grep network / mock usage | ❌ **FAIL** | Frontend currently bypasses backend completely by consuming hardcoded mock data in `mockDb.ts`. Zero backend API calls exist. |
| **No frontend logic duplicates ML** | Algorithmic audit in `frontend/src` | ❌ **FAIL** | `frontend/src/utils/skillGapAlgorithm.ts` duplicates course-skill gap calculations, alignment scores, and recommendations. |
| **No circular dependencies** | Import graph trace | ✅ **PASS** | Clean linear module hierarchy. |
| **No hidden architecture violations** | AST & Runtime inspection | ❌ **FAIL** | Route signature violation (`ml_adapter: MLAdapter = None` missing `Depends`), broken Alembic tree (`down_revision=None`), wildcard CORS with credentials. |

---

## 3. Detailed Architectural Findings

### 3.1 Frontend Tier Violations
1. **Duplicate Business & ML Logic (`skillGapAlgorithm.ts`)**:
   - `frontend/src/utils/skillGapAlgorithm.ts` implements `calculateCourseSkillGap()` locally.
   - It computes delta gaps, sets threshold flags (`'High Skill Gap' | 'Moderate Skill Gap' | 'Aligned'`), calculates alignment percentages, and crafts recommendation strings.
   - **Architectural Mandate**: Frontend must only request data, display data, and send user actions. The ML engine owns gap analysis (`ml/gap/` and `MLService.compute_course_gaps`).
2. **Total API Decoupling (Mock Data Usage)**:
   - The UI components (`AdminDashboard`, `CourseDetail`, `DistrictDetail`, `EmergingSkills`, `EmployerPortal`, `EmployerResponses`, `LoginPage`) rely on `INITIAL_COURSES`, `INITIAL_JOBS`, `INITIAL_SKILL_DEMANDS`, and `INITIAL_COURSE_SKILLS` from `src/data/mockDb.ts`.
   - Zero `fetch` or `axios` clients exist in `frontend/src/`.
   - Forms (e.g. `EmployerPortal`) append submissions to local React state instead of dispatching to `/api/v1/jobs/` or `/api/v1/employers/feedback`.
3. **Legacy Artifact Presence (`frontend/SkillMesh`)**:
   - An entire legacy Flask SQLite project (`SkillMesh/` containing `app.py`, `skillmesh.db`, `templates/`, and `static/`) was checked into `frontend/`.
   - A modal component (`PythonProjectModal.tsx`) allowed viewing this legacy code.
   - This causes repository bloat and architectural confusion.

### 3.2 Backend Tier Violations
1. **Broken FastAPI Dependency Injection in Route Signatures**:
   - In `routes_jobs.py`, `routes_employers.py`, and `routes_ml.py`, parameters were annotated as:
     ```python
     def create_job_posting(
         job_in: JobCreateSchema,
         db = None,
         ml_adapter: MLAdapter = None,
         _user = None
     ):
     ```
   - In FastAPI, parameters without `Depends(...)` are parsed as request body models. Because `MLAdapter` is not a Pydantic model, FastAPI raised:
     `fastapi.exceptions.FastAPIError: Invalid args for response field! Hint: check that MLAdapter is a valid Pydantic field type.`
   - This blocked app initialization and broke test discovery across the test suite.
2. **Divergent Router Registration in `main.py`**:
   - `main.py` registered `jobs_router`, `employers_router`, `ml_router`, `roles_router`, `students_router`.
   - Crucial endpoints (`/api/v1/auth`, `/api/v1/skills`, `/api/v1/courses`, `/api/v1/course-skills`, `/api/v1/job-postings`, `/api/v1/job-skills`, `/api/v1/user-skills`) in `app/api/` were not included.
3. **Security: Insecure CORS Configuration**:
   - `main.py` combined `allow_origins=["*"]` with `allow_credentials=True`, which is invalid under browser standards and poses CSRF/origin leakage risks.

### 3.3 ML Engine Tier Inspection
1. **Module Independence**:
   - The ML layer strictly fulfills the headless library requirement: no web framework, no ORM, no database connections.
   - All 39 unit tests in `ml/api/test_service.py` execute deterministically in under 2 seconds.
2. **Ingestion Loader Robustness**:
   - `ml/ingestion/loaders.py` had an unhandled top-level `import pyarrow.parquet as pq` and a hardcoded author local directory (`C:\Users\Nehal Jois\...`).
   - When running tests without `pyarrow`, imports of `loaders.py` crashed.
   - Resolving this to a graceful optional import ensures repository portability.

### 3.4 Database & Schema Integrity
1. **Alembic Disconnected Head**:
   - `backend/alembic/versions/001_phase10_student_role_schema.py` had `down_revision = None`.
   - Migration `49ecdd8f4657_create_job_posting_tables.py` had `revision = '49ecdd8f4657'`, creating two disjoint migration heads and breaking `alembic upgrade head`.

---

## 4. Remediation Plan

1. **Frontend**:
   - Build a centralized typed API client layer (`src/api/`).
   - Wire all UI pages and dashboards to real backend endpoints (`/api/v1/*`).
   - Delete client-side `skillGapAlgorithm.ts` and replace with ML backend responses (`/api/v1/ml/course-gaps` and `/api/v1/ml/students/.../gap/...`).
   - Add real Student, Institute, Trainer, Employer, and Admin portals.
   - Remove legacy `SkillMesh/` directory and `PythonProjectModal.tsx`.
2. **Backend**:
   - Correct all route parameter annotations to use `Depends(get_db)`, `Depends(get_ml_adapter)`, `Depends(get_current_user)`.
   - Register all routers in `main.py` under `/api/v1`.
   - Correct CORS configuration to explicit origins.
3. **ML**:
   - Make `pyarrow` imports in `ml/ingestion/loaders.py` resilient and remove hardcoded developer paths.
4. **Database**:
   - Link Alembic migration `001_phase10` to `49ecdd8f4657`.
   - Harmonize SQLAlchemy models and constraints.
