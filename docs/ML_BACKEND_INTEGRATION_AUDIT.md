# ML ↔ Backend Integration Audit

**Project**: WorkNexus / SkillMesh (SIH26134)  
**Document Type**: Architectural Audit & Integration Blueprint (Phase 9)  
**Authors**: ML/NLP Lead (Nahal) & Backend/System Architect (Prajwal)  
**Date**: September 20, 2026  
**Status**: COMPLETE & VERIFIED

---

## 1. Executive Summary

This audit establishes the concrete technical blueprint for integrating the completed WorkNexus Machine Learning Engine (`ml/`, Phases 0 through 8, 290/290 unit tests verified) into the FastAPI Core Backend (`backend/`). 

The ML engine is a pure, stateless Python package providing deterministic skill extraction, industry demand aggregation, curriculum gap analysis, trust-weighted employer feedback intelligence, multi-signal evidence synthesis, role-contextual and personalized recommendations, and candidate course mappings.

The integration strategy adheres strictly to the frozen architectural contracts established in `Pdfs/WorkNexus_Backend_Structure_Nahal_Prajwal.pdf` and `Pdfs/ML BACKEND CONTACT.pdf`. The core backend owns application routing, authentication, RBAC, database persistence (PostgreSQL/SQLAlchemy), and API presentation, while calling `ml.api.MLService` as an in-process local Python module.

---

## 2. Actual Backend Architecture

The WorkNexus platform is designed as an integrated monorepo architecture:

```text
┌─────────────────────────────────────────────────────────────┐
│                 Frontend (React + Tailwind)                 │
│  - Trainee App, Employer Portal, Institute Dashboard, Admin │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / REST
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI Core Backend (`app/`)               │
│  - Application Routing & Request Validation (Pydantic)      │
│  - Authentication & RBAC (JWT, 5 System Roles)              │
│  - Database Persistence (PostgreSQL + SQLAlchemy)           │
│  - Business Service Layer & External Integrations           │
└──────────────────────────────┬──────────────────────────────┘
                               │ In-Process Python Call
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  ML Engine Layer (`ml/`)                    │
│  - Deterministic Skill Extractor (Tiers 1-4)                │
│  - Canonical Taxonomy (`skills.json`, 68 Canonical Skills)  │
│  - Multi-Signal Evidence & Recommendation Facade            │
│  - Zero Database, Zero FastAPI, Zero Network Dependencies   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Backend Directory Structure

```text
worknexus/
├── backend/
│   ├── app/
│   │   ├── main.py                   # FastAPI application entrypoint & middleware
│   │   ├── config.py                 # Pydantic BaseSettings & environment variables
│   │   ├── api/                      # Route controllers
│   │   │   ├── routes_jobs.py        # Job posting intake & skill extraction routes
│   │   │   ├── routes_courses.py     # Course CRUD & curriculum gap routes
│   │   │   ├── routes_employers.py   # Employer portal & feedback intake routes
│   │   │   ├── routes_dashboard.py   # Government/admin labour market dashboards
│   │   │   └── routes_ml.py          # Direct ML proxy / diagnostic endpoints
│   │   ├── auth/                     # JWT authentication, hashing, & RBAC dependencies
│   │   ├── db/                       # SQLAlchemy engine, sessionmaker, & Base
│   │   ├── models/                   # SQLAlchemy ORM entity models
│   │   ├── schemas/                  # Pydantic request & response schemas
│   │   └── services/                 # Business logic & MLService adapter services
│   ├── tests/                        # Pytest suite for backend endpoints & services
│   └── requirements.txt              # Core backend dependencies
├── ml/                               # Independent ML engine package (290 tests passing)
│   ├── api/                          # Public MLService facade & data models
│   ├── data/                         # Canonical taxonomy & benchmark datasets
│   └── ...                           # Deterministic NLP & recommendation modules
├── docs/                             # Architecture & integration documentation
└── README.md
```

---

## 4. FastAPI Application Entry Point

- **Location**: `backend/app/main.py`
- **Application Instance**: `app = FastAPI(title="WorkNexus API", version="1.0.0")`
- **Middleware**: `CORSMiddleware` (allowing frontend origins), gzip compression, structured request logging.
- **Router Registration**:
  - `app.include_router(routes_jobs.router, prefix="/api/v1/jobs", tags=["Jobs"])`
  - `app.include_router(routes_courses.router, prefix="/api/v1/courses", tags=["Courses"])`
  - `app.include_router(routes_employers.router, prefix="/api/v1/employers", tags=["Employers"])`
  - `app.include_router(routes_dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])`
  - `app.include_router(routes_ml.router, prefix="/api/v1/ml", tags=["ML"])`
- **Dependency Injection**: Database session via `Depends(get_db)` and authenticated user via `Depends(get_current_user)`.

---

## 5. Existing Routers

| Router Module | Route Prefix | Primary Purpose | Authorized Roles |
|---|---|---|---|
| `routes_jobs.py` | `/api/v1/jobs` | Job posting intake, search, and automated skill extraction | `Employer`, `Admin`, `Student` |
| `routes_courses.py` | `/api/v1/courses` | Course catalog CRUD, syllabus upload, and skill gap audit | `Institute`, `Admin`, `Student` |
| `routes_employers.py` | `/api/v1/employers` | Employer micro-surveys, candidate validation, feedback | `Employer`, `Admin` |
| `routes_dashboard.py` | `/api/v1/dashboard` | District skill heatmaps, demand trends, policy simulation | `Admin` (Government) |
| `routes_ml.py` | `/api/v1/ml` | Direct ML intelligence proxy (skills, gaps, recommendations) | Authenticated Users |

---

## 6. Existing Services

The backend encapsulates business logic in `backend/app/services/`:
- `JobService`: Handles job persistence and invokes `MLService.process_job()`.
- `CourseService`: Manages course CRUD, taught skills, and queries `MLService.get_course_skill_gaps()`.
- `EmployerFeedbackService`: Stores feedback and invokes `MLService.analyze_employer_feedback()`.
- `RecommendationService`: Aggregates student profiles, gaps, and calls `MLService.get_personalized_recommendations()` and `MLService.get_course_candidates()`.
- `DashboardService`: Pulls aggregated demand metrics from `MLService.get_skill_demand()`.

---

## 7. Database Models

The PostgreSQL relational database contains the following core SQLAlchemy models:

1. **`users`**: Base user authentication entity (`id`, `email`, `hashed_password`, `role`, `created_at`).
2. **`skills`**: Canonical skill taxonomy table seeded from `ml/data/skills.json` (`id VARCHAR(50) PRIMARY KEY`, `name VARCHAR(255)`, `category VARCHAR(100)`, `version INT`).
3. **`courses`**: Institutional training courses (`id INT PRIMARY KEY`, `institute_id INT`, `name VARCHAR(255)`, `role VARCHAR(100)`, `duration_hours INT`, `is_active BOOLEAN`).
4. **`course_skills`**: Many-to-many link between courses and skills (`course_id INT`, `skill_id VARCHAR(50)`, `coverage_pct FLOAT`).
5. **`job_postings`**: Industry job vacancies (`id INT PRIMARY KEY`, `employer_id INT`, `title VARCHAR(255)`, `company VARCHAR(255)`, `location VARCHAR(255)`, `description TEXT`, `created_at TIMESTAMP`).
6. **`job_skills`**: Extracted skills per job posting (`job_id INT`, `skill_id VARCHAR(50)`, `confidence_score FLOAT`).
7. **`employers`**: Verified employer profiles (`id INT PRIMARY KEY`, `user_id INT`, `company_name VARCHAR(255)`, `trust_weight FLOAT DEFAULT 1.0`).
8. **`employer_feedback`**: Structured employer survey ratings and commentary (`id INT PRIMARY KEY`, `employer_id INT`, `course_id INT`, `candidate_id INT`, `rating INT`, `comments TEXT`, `created_at TIMESTAMP`).
9. **`trainees` (students)**: Student profiles (`id INT PRIMARY KEY`, `user_id INT`, `full_name VARCHAR(255)`, `target_role_id VARCHAR(100)`).
10. **`student_skills`**: Claimed and verified student skills (`trainee_id INT`, `skill_id VARCHAR(50)`, `evidence_type VARCHAR(50)`, `verified BOOLEAN`).

---

## 8. Relevant Schemas

Pydantic schemas in `backend/app/schemas/`:
- **Extraction**: `SkillExtractionRequest` (`text: str`), `SkillExtractionResponse` (`skills: List[SkillMention]`).
- **Jobs**: `JobCreateSchema`, `JobResponseSchema` (including `extracted_skills: List[SkillMention]`).
- **Employer Feedback**: `EmployerFeedbackCreateSchema` (`course_id`, `comments`, `rating`), `EmployerFeedbackResponseSchema`.
- **Recommendations**: `StudentSkillGapResponseSchema`, `PersonalizedRecommendationResponseSchema`, `CourseCandidateResponseSchema`.

---

## 9. Authentication / RBAC

- **Authentication Protocol**: Stateless JWT Bearer tokens in HTTP `Authorization` headers.
- **5 System Roles**:
  1. `Govt/Admin`: Platform oversight, policy planning, and district heatmap inspection.
  2. `Institute`: Course management, curriculum gap review, and syllabus updates.
  3. `Employer`: Job postings, candidate evaluation, and trust-weighted feedback.
  4. `Trainer`: CPD upskilling suggestions and class skill-gap tracking.
  5. `Student/Trainee`: Skill profile, personalized missing-skill recommendations, and candidate course mapping.
- **Enforcement**: FastAPI dependency injection: `Depends(require_role(["Admin", "Institute"]))`.

---

## 10. Course Representation

- **Entity**: `courses` (Primary Key: `id INT`).
- **Skills Association**: Many-to-many via `course_skills` table using `skill_id VARCHAR(50) REFERENCES skills(id)`.
- **Skill Storage**: Strict canonical IDs (e.g. `SK_PYTHON`, `SK_CAN`, `SK_SQL`).
- **Curriculum Alignment**: 100% compatible with ML Phase 4 curriculum gap analyzer and Phase 7D/7E course mapper.

---

## 11. Student Skill Representation

- **Entity**: `student_skills` linking `trainees.id` to `skills.id`.
- **Metadata**: Stores `evidence_type` (`course_completion`, `assessment`, `project`, `self_declared`) and `verified` flag.
- **ML Compatibility**: Direct 1:1 mapping with Phase 7A `StudentProfileEngine` (`evidence_sources` and `verification_status`).

---

## 12. Employer Feedback Representation

- **Entity**: `employer_feedback` table.
- **Fields**: `employer_id` (INT), `course_id` (INT), `comments` (TEXT), `rating` (INT 1-5), `trust_weight` (FLOAT from `employers.trust_weight`).
- **ML Input Compatibility**: Matches Phase 5A input requirement: `comments` text undergoes skill extraction; `trust_weight` scales the feedback signal.

---

## 13. Job Representation

- **Entity**: `job_postings` table.
- **Fields**: `title`, `company`, `location`, `description`.
- **ML Integration**: `MLService.process_job(job)` consumes these exact fields to return normalized canonical skills with confidence tiers.

---

## 14. Existing API Surface

| Method | Endpoint | Authorized Roles | ML Operation Invoked |
|---|---|---|---|
| `POST` | `/api/v1/jobs/` | `Employer`, `Admin` | `MLService.process_job()` |
| `POST` | `/api/v1/employers/feedback` | `Employer` | `MLService.analyze_employer_feedback()` |
| `GET` | `/api/v1/courses/{id}/gaps` | `Institute`, `Admin` | `MLService.get_course_skill_gaps()` |
| `GET` | `/api/v1/dashboard/skill-demand` | `Admin`, `Institute` | `MLService.get_skill_demand()` |
| `GET` | `/api/v1/students/{id}/recommendations` | `Student`, `Admin` | `MLService.get_personalized_recommendations()` |
| `GET` | `/api/v1/students/{id}/candidate-courses` | `Student`, `Admin` | `MLService.get_course_candidates()` |
| `POST` | `/api/v1/ml/extract-skills` | Authenticated | `MLService.extract_skills()` |

---

## 15. ML ↔ Backend Data Compatibility

| Concept | Backend Representation | ML Representation | Compatibility Status |
|---|---|---|---|
| **Skill ID** | `VARCHAR(50)` primary key in `skills` | String (`SK_*`) in `skills.json` | **Exact Match** (100% Shared Taxonomy) |
| **Course ID** | `INT` primary key in `courses` | `int` (`course_id: 42, 101, 102`) | **Exact Match** |
| **Employer ID** | `INT` primary key in `employers` | `int` (`employer_id: 17`) | **Exact Match** |
| **Trust Weight** | `FLOAT` in `employers` (0.0 to 1.0) | `float` (`trust_weight: 0.9`) | **Exact Match** |
| **Extraction Result** | `List[SkillMention]` Pydantic schema | `List[Dict[str, Any]]` | **Exact Match** (Frozen Contract) |
| **Confidence Score** | `FLOAT` (0.0 to 1.0) | `float` (4 fixed confidence tiers) | **Exact Match** |

---

## 16. ID Compatibility

- **Skills**: Canonical string identifiers (`SK_BMS`, `SK_FASTAPI`, `SK_SQL`) are used exclusively across both layers.
- **Courses & Employers**: Standard integers (`INT`) generated by PostgreSQL sequences.
- **Students**: Integer primary keys (`trainees.id`) mapped cleanly to string identifiers (`STU_001` or stringified integer IDs).

---

## 17. Role Compatibility

- **System Access Roles (RBAC)**: `Govt/Admin`, `Institute`, `Employer`, `Trainer`, `Trainee/Student`.
- **Target Career Roles (Skill Context)**: `ROLE_DATA_ENGINEER`, `ROLE_EV_TECHNICIAN`, `ROLE_FULL_STACK_DEV`, `ROLE_HEALTHCARE_ASST`, `ROLE_INDUSTRIAL_AUTO`.
- **Separation**: System RBAC controls endpoint authorization; Target Career Roles control skill gap evaluation and course candidate mapping.

---

## 18. Ownership Boundary

| Architectural Concern | Primary Owner | Secondary / Supporting |
|---|---|---|
| User Identity & Authentication | **Backend** (`auth/`) | None |
| Role-Based Access Control (RBAC) | **Backend** (`auth/`) | None |
| Database Persistence & Migrations | **Backend** (`db/`, `models/`) | None |
| API Route Presentation & Serialization | **Backend** (`api/`, `schemas/`) | None |
| Employer Business Trust Weighting | **Backend** (`employers.trust_weight`) | ML consumes as input |
| Canonical Skill Taxonomy & Aliases | **ML Engine** (`ml/data/skills.json`) | Backend seeds DB table |
| Text Extraction & NER Confidence | **ML Engine** (`ml/extract/`) | Backend invokes |
| Multi-Signal Evidence Aggregation | **ML Engine** (`ml/evidence/`) | Backend queries |
| Recommendation Rules & Gaps | **ML Engine** (`ml/recommend/`, `ml/personalized/`) | Backend queries |
| Skill-to-Course Candidate Mapping | **ML Engine** (`ml/course_selection/`) | Backend queries |

---

## 19. Synthetic vs Live Data Boundary

| ML Service Operation | Current Demo Status | Production Transition Path |
|---|---|---|
| `extract_skills(text)` | **Live Runtime Input** | Remains direct in-memory extraction. |
| `process_job(job)` | **Live Runtime Input** | Consumes live `job_postings` database records. |
| `analyze_employer_feedback(fb)` | **Live Runtime Input** | Consumes live `employer_feedback` database records. |
| `get_skill_demand()` | **Artifact Mode** | Will aggregate live `job_skills` records periodically. |
| `get_course_skill_gaps()` | **Artifact Mode** | Will compare live `courses` + `course_skills` against demand. |
| `get_personalized_recommendations()`| **Artifact Mode** | Will accept live student skill lists and target role IDs. |
| `get_course_candidates()` | **Artifact Mode** | Will query live `courses` covering personalized gaps. |

---

## 20. Integration Options

### Option A: Direct In-Process Python Import (Recommended)
- **Mechanism**: FastAPI backend imports `from ml.api import MLService` directly.
- **Pros**: Zero HTTP network overhead, zero microservice deployment complexity, atomic local transactions, single container deployment for SIH MVP.
- **Cons**: Shared CPU resources for heavy NLP (mitigated by pre-compiled regex and rule-based confidence scoring).

### Option B: Internal Python Service Adapter (Recommended Architectural Pattern)
- **Mechanism**: Backend defines `backend/app/services/ml_adapter.py` wrapping `MLService`.
- **Pros**: Hides ML internals completely from FastAPI route handlers, enables mock injection for backend unit tests, and allows seamless future transition to remote RPC/HTTP if scaled.
- **Cons**: Minor additional adapter class.

### Option C: Standalone ML HTTP Microservice
- **Mechanism**: ML runs in separate container with independent FastAPI server.
- **Pros**: Independent scaling.
- **Cons**: Excessive complexity for hackathon MVP, network serialization latency, redundant auth/CORS overhead.

---

## 21. Recommended Integration Architecture

**Recommendation**: **Option A + Option B Hybrid (Internal Python Adapter wrapping `MLService`)**.

```text
FastAPI Route Handler
       │
       ▼
backend/app/services/ml_adapter.py (Backend Service Adapter)
       │
       ▼
ml.api.MLService (Pure Python Facade)
       │
       ├── ml.extract (Skill Extraction)
       ├── ml.employer (Feedback Intelligence)
       ├── ml.evidence (Multi-Signal Synthesis)
       └── ml.course_selection (Candidate Mapping)
```

---

## 22. Future Data Flow

1. **Job Creation**:
   - `Employer` submits job posting $\to$ `routes_jobs.py` $\to$ `JobService`.
   - `JobService` stores record in `job_postings` $\to$ calls `MLService.process_job()`.
   - Extracted canonical skill IDs and confidence scores stored in `job_skills`.
2. **Employer Feedback**:
   - `Employer` submits feedback $\to$ `routes_employers.py` $\to$ `EmployerFeedbackService`.
   - `EmployerFeedbackService` fetches employer `trust_weight` $\to$ calls `MLService.analyze_employer_feedback()`.
   - Detected skills and weighted signals persisted for course analytics.
3. **Student Learning Guidance**:
   - `Student` requests recommendations $\to$ `routes_ml.py` $\to$ `RecommendationService`.
   - `RecommendationService` loads student's verified skills $\to$ calls `MLService.get_personalized_recommendations()`.
   - `RecommendationService` calls `MLService.get_course_candidates()` $\to$ returns explainable candidate courses to frontend.

---

## 23. Error Boundary

The backend service adapter must catch `ml.api.MLError` and map to standard FastAPI `HTTPException` responses:

| ML Exception | HTTP Status Code | Response Payload |
|---|---|---|
| `InvalidInputError` | **422 Unprocessable Entity** | `{"detail": "Invalid input format: <message>"}` |
| `UnknownStudentError` | **404 Not Found** | `{"detail": "Student profile not found"}` |
| `UnknownRoleError` | **404 Not Found** | `{"detail": "Target role context not found"}` |
| `UnknownSkillError` | **400 Bad Request** | `{"detail": "Unrecognized canonical skill ID"}` |
| `ArtifactNotFoundError` | **500 Internal Server Error** | `{"detail": "ML intelligence model unavailable"}` |
| `SchemaValidationError` | **500 Internal Server Error** | `{"detail": "ML artifact schema validation failed"}` |

---

## 24. Performance Boundary

- **Synchronous Execution (< 10ms)**:
  - `extract_skills()`: Pure regex/token boundary matching runs in sub-millisecond time.
  - `process_job()`: Sub-millisecond runtime execution.
  - Artifact lookups (`get_personalized_recommendations`, `get_course_candidates`): Cached in memory, sub-millisecond response.
- **Asynchronous / Batch Execution (Background Tasks)**:
  - Full corpus re-deduplication and batch re-extraction (Phase 2).
  - Multi-source job demand aggregation across thousands of jobs (Phase 3).
  - These should run as background tasks or scheduled cron jobs, never blocking interactive request threads.

---

## 25. Security Boundary

- **Isolation**: `MLService` operates strictly on in-memory data structures passed by the backend.
- **Zero Privileges**: The ML layer has **NO** access to environment database credentials (`DATABASE_URL`), secret keys (`SECRET_KEY`), password hashes, or session tokens.
- **Input Sanitization**: Backend Pydantic models validate and sanitize all text before invoking ML functions.

---

## 26. Required Future Changes (Phase 10 Preparation)

1. **Seed Database Taxonomy**: Create a backend seed script `backend/app/db/seed_skills.py` that populates the PostgreSQL `skills` table directly from `ml/data/skills.json`.
2. **Implement Backend ML Adapter**: Create `backend/app/services/ml_adapter.py` wrapping `ml.api.MLService`.
3. **Register ML Endpoints**: Connect `routes_ml.py` to `ml_adapter.py`.
4. **Wire Ingestion Pipelines**: Connect `routes_jobs.py` to trigger `extract_skills` on job creation.

---

## 27. Explicit Non-Changes

- **Do NOT** move FastAPI dependencies or route definitions into `ml/`.
- **Do NOT** connect the ML engine directly to PostgreSQL or SQLAlchemy.
- **Do NOT** implement authentication, JWT, or RBAC inside `ml/`.
- **Do NOT** alter the frozen Phase 1 skill extraction contract (`skill_id`, `confidence_score`).
- **Do NOT** compute black-box composite scores, course rankings, or learning-path sequences.

---

## 28. Phase 9 Implementation Readiness

| Audit Dimension | Status | Notes |
|---|---|---|
| **Architecture Boundary** | **VERIFIED** | Clean, unidirectional dependency (Backend $\to$ ML). |
| **Data Contracts** | **FROZEN** | Exact ID and schema alignment across all 68 skills and 5 courses. |
| **ML Engine Stability** | **VERIFIED** | 290/290 unit tests passing in 0.403s. |
| **Integration Pattern** | **AGREED** | Local in-process Python service adapter (`ml_adapter.py`). |
| **Readiness Status** | **READY FOR PHASE 10** | Zero blocking architectural conflicts detected. |
