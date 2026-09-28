# PHASE 9A — ML ↔ BACKEND INTEGRATION FOUNDATION
===================================================================
**Project:** WorkNexus / SkillMesh (Smart India Hackathon 2026)  
**Branch:** ml-dev  
**Status:** COMPLETE & VERIFIED (302/302 Total Tests Passing)  
**Execution Date:** September 2026  

---

## 1. Executive Summary & Objective

Phase 9A establishes the first production integration boundary between the **FastAPI Backend** and the **ML Intelligence Engine** (`ml.api.MLService`). 

Prior to Phase 9A, the ML pipeline operated in benchmark/artifact mode across Phases 0.5 through 8. Phase 9 completed an architectural audit to define the integration contract. Phase 9A implements the **in-process Python adapter layer** (`backend/app/services/ml_adapter.py`) bridging the core backend with the ML engine for the three approved runtime-input operations:
1. **Skill Extraction** (`extract_skills(text)`)
2. **Job Posting Ingestion Intelligence** (`process_job(job)`)
3. **Employer Feedback Signal Intelligence** (`analyze_employer_feedback(feedback)`)

### Key Design Invariants Preserved
- **Single In-Process Python Runtime**: No separate ML HTTP microservice, avoiding network overhead, serialization latency, and deployment complexity.
- **Strict Boundary Separation**:
  - **Backend owns**: FastAPI application lifecycle, HTTP routes, RBAC/auth, Pydantic request/response validation, database models, persistence, and HTTP error mapping.
  - **ML owns**: Canonical taxonomy matching, tokenization, confidence scoring, multi-signal evidence aggregation, and trust-weighted employer signal calculations.
- **Zero Cross-Contamination**: No database ORM or FastAPI dependencies inside `ml/`. No ML algorithm logic duplicated inside `backend/`.
- **Single Point of Entry**: `backend/app/services/ml_adapter.py` is the only backend component permitted to import `MLService`.

---

## 2. System Architecture & In-Process Flow

```
+------------------------------------------------------------------------+
|                        FastAPI Core Backend                            |
|                                                                        |
|   HTTP Client / Frontend (React / Mobile)                              |
|         |                                                              |
|         v [JSON / REST + JWT Auth Headers]                             |
|   +----------------------------------------------------------------+   |
|   | API Routes (RBAC Enforced)                                     |   |
|   |  - POST /api/v1/ml/extract-skills       (Public / All Roles)   |   |
|   |  - POST /api/v1/jobs/                   (Employer / Admin)     |   |
|   |  - POST /api/v1/employers/feedback      (Employer / Admin)     |   |
|   +-------------------------------+--------------------------------+   |
|                                   |                                    |
|                                   v                                    |
|   +----------------------------------------------------------------+   |
|   | Backend Service Layer                                          |   |
|   |  - JobService         (Persistence + DB Transaction)           |   |
|   |  - EmployerService    (Persistence + DB Transaction)           |   |
|   +-------------------------------+--------------------------------+   |
|                                   |                                    |
|                                   v                                    |
|   +----------------------------------------------------------------+   |
|   | In-Process ML Adapter (backend/app/services/ml_adapter.py)     |   |
|   |  - Input normalization & DTO mapping                           |   |
|   |  - ML domain exception -> HTTPException translation            |   |
|   +-------------------------------+--------------------------------+   |
+-----------------------------------+------------------------------------+
                                    | In-Process Direct Method Calls
                                    v
+------------------------------------------------------------------------+
|                         ML Intelligence Engine                         |
|                                                                        |
|   +----------------------------------------------------------------+   |
|   | ml.api.MLService (Public Facade)                               |   |
|   |  - extract_skills()                                            |   |
|   |  - process_job()                                               |   |
|   |  - analyze_employer_feedback()                                 |   |
|   +-------------------------------+--------------------------------+   |
|                                   |                                    |
|   +-------------------------------+--------------------------------+   |
|   | Core ML Subsystems (Internal)                                  |   |
|   |  - ml.extract.extractor (N-gram tokenizer & substring matcher) |   |
|   |  - ml.employer.feedback_analyzer (Trust-weighted scoring)      |   |
|   |  - ml/data/skills.json (Canonical 40-skill taxonomy v1)        |   |
|   +----------------------------------------------------------------+   |
+------------------------------------------------------------------------+
```

---

## 3. Directory Layout & Module Structure

```
SIH/
├── backend/
│   ├── app/
│   │   ├── config.py                  # Environment & DB Settings
│   │   ├── main.py                    # FastAPI application factory & router registration
│   │   ├── api/
│   │   │   ├── routes_jobs.py         # POST /api/v1/jobs/
│   │   │   ├── routes_employers.py    # POST /api/v1/employers/feedback
│   │   │   └── routes_ml.py           # POST /api/v1/ml/extract-skills
│   │   ├── auth/
│   │   │   └── rbac.py                # CurrentUser & require_role dependency
│   │   ├── db/
│   │   │   └── session.py             # Database session & repository abstractions
│   │   ├── models/
│   │   │   └── entities.py            # Normalized domain entities
│   │   ├── schemas/
│   │   │   └── schemas.py             # Pydantic request/response schemas
│   │   └── services/
│   │       ├── ml_adapter.py          # Unified In-Process ML Bridge
│   │       ├── job_service.py         # Job creation orchestration & skill linking
│   │       └── employer_service.py    # Feedback ingestion & signal computation
│   ├── requirements.txt               # Backend dependencies
│   └── tests/
│       ├── test_ml_adapter.py         # Adapter unit tests & exception mapping
│       ├── test_job_integration.py    # Job creation + ML extraction persistence
│       ├── test_employer_feedback_integration.py # Feedback + weighted signal persistence
│       └── test_routes.py             # HTTP status codes, headers & RBAC verification
├── docs/
│   ├── ML_BACKEND_INTEGRATION_AUDIT.md
│   └── PHASE_9A_ML_BACKEND_INTEGRATION.md
└── ml/
    ├── api/                           # Phase 8 ML Public Service Layer
    ├── data/                          # Canonical Datasets & Taxonomy
    ├── extract/                       # Skill Extraction Engine
    └── employer/                      # Employer Feedback Engine
```

---

## 4. API Endpoints & RBAC Matrix

| Endpoint | Method | Allowed Roles | Description | Response Model | HTTP Codes |
| :--- | :---: | :---: | :--- | :--- | :---: |
| `/health` | `GET` | Public | Backend health check | `{"status": "healthy"}` | 200 |
| `/api/v1/ml/extract-skills` | `POST` | Authenticated (All) | Direct proxy to extract canonical skills from text | `SkillExtractionResponse` | 200, 401, 422, 500 |
| `/api/v1/jobs/` | `POST` | `Employer`, `Admin` | Create job posting, trigger skill extraction, persist skills | `JobResponseSchema` | 201, 401, 403, 422, 500 |
| `/api/v1/employers/feedback` | `POST` | `Employer`, `Admin` | Ingest feedback, extract skills, compute trust-weighted signals | `EmployerFeedbackResponseSchema` | 201, 401, 403, 422, 500 |

---

## 5. In-Process ML Adapter Implementation (`ml_adapter.py`)

`backend/app/services/ml_adapter.py` acts as the single gateway to the ML engine:

### Domain Exception Translation Table

| ML Exception (`ml.api`) | HTTP Exception (`fastapi`) | Status Code | Reason |
| :--- | :--- | :---: | :--- |
| `InvalidInputError` | `HTTPException` | `422 Unprocessable Entity` | Malformed text, empty strings, missing fields |
| `UnknownSkillError` | `HTTPException` | `404 Not Found` | Skill ID not found in canonical taxonomy |
| `ArtifactNotFoundError` | `HTTPException` | `500 Internal Server Error` | Underlying ML artifact file missing |
| `MLError` (Base) | `HTTPException` | `500 Internal Server Error` | Unhandled ML engine failure |

---

## 6. End-to-End Execution Flows

### A. Job Posting Creation with Automated Skill Extraction
1. **Employer** posts job payload to `POST /api/v1/jobs/` with JWT header.
2. `rbac.require_role(["Employer", "Admin"])` authenticates user and enforces permissions.
3. `routes_jobs.py` routes request to `JobService.create_job(db, job_in, ml_adapter)`.
4. `JobService` calls `ml_adapter.process_job(job_in)`:
   - ML combines title + description text.
   - Exact string and substring matching executes against canonical `skills.json` taxonomy.
   - Extracted canonical skills returned with confidence scores (e.g. `[{"skill_id": "SK_PYTHON", "confidence_score": 0.98}]`).
5. `JobService` creates `JobPosting` and `JobSkill` entity records.
6. DB transaction commits atomically and returns `JobResponseSchema` with `extracted_skills`.

### B. Employer Feedback Ingestion with Trust-Weighted Signal Intelligence
1. **Employer** submits feedback to `POST /api/v1/employers/feedback`.
2. `rbac.require_role(["Employer", "Admin"])` validates role.
3. `EmployerService.submit_feedback(db, feedback_in, ml_adapter)`:
   - Queries DB for employer record to obtain authoritative `trust_weight` (defaults to 1.0).
   - Invokes `ml_adapter.analyze_employer_feedback({feedback_id, employer_id, comments, trust_weight})`.
   - ML extracts skills mentioned in comments and multiplies `confidence_score * trust_weight` to calculate `weighted_signal`.
4. Persists `EmployerFeedback` and associated `EmployerFeedbackSignal` records into the database.
5. Returns `EmployerFeedbackResponseSchema` with detailed extracted signals.

### C. Direct Skill Extraction Proxy
1. Any authenticated user sends raw text to `POST /api/v1/ml/extract-skills`.
2. `routes_ml.py` invokes `ml_adapter.extract_skills(text)`.
3. Returns `SkillExtractionResponse` containing list of canonical `SkillExtractionItem` records.

---

## 7. Verification & Test Suite Execution

Both test suites run completely deterministically and pass with zero errors:

### Backend Test Suite (12 Tests Passing)
```bash
python -m unittest discover -s backend/tests -p "test_*.py"
```
- `test_ml_adapter.py`: 4/4 passing (success extraction, 422 error mapping, job processing, feedback trust weighting).
- `test_job_integration.py`: 1/1 passing (entity persistence and skill linking).
- `test_employer_feedback_integration.py`: 1/1 passing (feedback persistence and weighted signals).
- `test_routes.py`: 6/6 passing (health check, extract-skills route, job authorized/forbidden, feedback authorized/forbidden).

### ML Engine Test Suite (290 Tests Passing)
```bash
python -m unittest discover -s ml -p "test_*.py"
```
- Total test modules: 11 phases (`test_ingestion`, `test_dedup`, `test_extractor`, `test_batch_extractor`, `test_demand_analyzer`, `test_gap_analyzer`, `test_employer_feedback`, `test_evidence_aggregator`, `test_recommender`, `test_context_recommender`, `test_student_profile`, `test_student_gap`, `test_personalized_recommender`, `test_course_mapper`, `test_course_selector`, `test_ml_service`).
- Execution Time: 0.274s.
- Zero regressions.

---

## 8. Summary of Completed Deliverables

1. **`backend/app/services/ml_adapter.py`**: Complete, unified in-process bridge with dependency injection and error mapping.
2. **`backend/app/api/`**: `routes_jobs.py`, `routes_employers.py`, `routes_ml.py`, `backend/app/main.py`.
3. **`backend/app/auth/rbac.py`**: Role-based access control supporting `Admin`, `Employer`, `Institute`, `Trainer`, and `Student`.
4. **`backend/app/models/entities.py`**: Normalized entities for Users, Skills, Courses, Jobs, and Feedback Signals.
5. **`backend/app/schemas/schemas.py`**: Validated DTO schemas for requests and responses.
6. **`backend/tests/`**: Comprehensive test coverage across unit, integration, and HTTP route levels.
7. **Documentation**: `docs/PHASE_9A_ML_BACKEND_INTEGRATION.md` and updated `ml/README.md`.
