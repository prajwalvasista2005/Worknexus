# WorkNexus / SkillMesh — ML Layer Integration Contract & Backend Handoff

**Project**: WorkNexus / SkillMesh (SIH 2026)  
**Layer Boundary**: Machine Learning Engine (`ml/`) $\longleftrightarrow$ FastAPI Core Backend  
**Status**: Authoritative Integration Contract (Phase 8)

---

## 1. Architectural Boundary & Separation of Concerns

```text
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Web / UI)                      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Core Backend                      │
│                                                             │
│  - User Authentication, JWT, & Sessions                     │
│  - RBAC (Student, Employer, Admin, Instructor Roles)        │
│  - Database Persistence (PostgreSQL, SQLAlchemy, Alembic)   │
│  - Course CRUD & Student Enrollment Management              │
│  - API Route Handlers & HTTP Serialization                  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼ calls via in-process Python
┌─────────────────────────────────────────────────────────────┐
│                    ML Engine (`ml/`)                        │
│                                                             │
│  - Skill Extraction (Exact, Regex, Fuzzy Tiers)             │
│  - Job Demand Aggregation & Source Normalization            │
│  - Curriculum Skill Gap Analysis                            │
│  - Employer Feedback Intelligence & Trust Weighting         │
│  - Multi-Signal Skill Evidence Aggregation                  │
│  - Generic & Context-Aware Skill Recommendations            │
│  - Student Skill Profiles, Gaps, & Personalized Recs        │
│  - Candidate Course Selection Mapping                       │
└─────────────────────────────────────────────────────────────┘
```

### Critical Architectural Rules
1. **Unidirectional Dependency**: The FastAPI backend imports and calls `MLService` as a standard local Python library.
2. **Zero Inward Calls**: The ML layer **NEVER** imports or calls FastAPI, SQL/database drivers, ORMs, authentication modules, or frontend assets.
3. **No Database Access in ML**: Persistence is 100% owned by the backend. The ML layer is stateless and operates strictly on passed arguments or validated benchmark artifacts.
4. **No Direct JSON Scraping by Backend**: The backend MUST NEVER parse internal ML artifact JSON files directly. All operations must pass through `MLService`.

---

## 2. Public ML Service Interface (`MLService`)

All ML operations are exposed via `ml.api.MLService`:

```python
from ml.api import MLService

service = MLService()
```

### Runtime Mode vs Artifact Benchmark Mode

| Function Name | Mode | Description |
|---|---|---|
| `extract_skills(text: str)` | **Runtime Live** | Extracts canonical skills and confidence scores from raw text. |
| `process_job(job: Union[dict, object])` | **Runtime Live** | Normalizes job title/description and extracts canonical skills. |
| `analyze_employer_feedback(feedback)` | **Runtime Live** | Extracts skills from employer comments with trust weighting. |
| `get_skill_demand()` | **Artifact Mode** | Retrieves aggregated job demand intelligence across market jobs. |
| `get_course_skill_gaps()` | **Artifact Mode** | Retrieves curriculum coverage against industry skill demand. |
| `get_skill_evidence()` | **Artifact Mode** | Retrieves multi-signal evidence combining job demand & employer feedback. |
| `get_skill_recommendations()` | **Artifact Mode** | Retrieves transparent, rule-based generic skill recommendations. |
| `get_role_skill_context(role_id: str)` | **Artifact Mode** | Retrieves contextual skill requirements for a target role. |
| `get_student_skill_profile(student_id: str)` | **Artifact Mode** | Retrieves student's verified skills with provenance evidence. |
| `get_student_skill_gap(student_id, role_id)` | **Artifact Mode** | Compares student skills against target role context. |
| `get_personalized_recommendations(student_id, role_id)` | **Artifact Mode** | Retrieves missing evidence-backed skill recommendations. |
| `get_course_candidates(student_id, role_id)` | **Artifact Mode** | Maps personalized skills to candidate catalog courses. |

---

## 3. Frozen Skill Extraction Contract

The skill extraction contract is **FROZEN** and must not be altered:

```python
results = service.extract_skills("Looking for Python, FastAPI, and Docker experience.")
```

**Output Schema**:
```json
[
  {
    "skill_id": "SK_PYTHON",
    "confidence_score": 0.96
  },
  {
    "skill_id": "SK_FASTAPI",
    "confidence_score": 0.96
  },
  {
    "skill_id": "SK_DOCKER",
    "confidence_score": 0.96
  }
]
```

---

## 4. Integration Examples for FastAPI Backend

### Example 1: Skill Extraction in Job Posting Endpoint
```python
from ml.api import MLService, MLError

ml_service = MLService()

def handle_job_post_creation(job_title: str, job_description: str):
    try:
        combined_text = f"{job_title}\n{job_description}"
        extracted_skills = ml_service.extract_skills(combined_text)
        return {"status": "success", "skills": extracted_skills}
    except MLError as e:
        return {"status": "error", "message": str(e)}
```

### Example 2: Personalized Student Recommendations
```python
from ml.api import MLService, UnknownStudentError, UnknownRoleError

ml_service = MLService()

def handle_get_student_recommendations(student_id: str, role_id: str):
    try:
        recs = ml_service.get_personalized_recommendations(student_id, role_id)
        candidates = ml_service.get_course_candidates(student_id, role_id)
        
        return {
            "student_id": recs.student_id,
            "role": recs.role,
            "recommended_skills": [
                r for r in recs.skill_recommendations
                if r.get("personalized_status") == "recommended"
            ],
            "candidate_courses": candidates.candidate_courses,
            "uncovered_skills": candidates.uncovered_personalized_skills
        }
    except (UnknownStudentError, UnknownRoleError) as e:
        return {"error": "NotFound", "message": str(e)}
```

---

## 5. Error Handling & Exceptions

All service-level exceptions inherit from `ml.api.MLError`:

| Exception Class | When Raised |
|---|---|
| `InvalidInputError` | Input argument is of wrong type or contains malformed values. |
| `ArtifactNotFoundError` | A required pipeline JSON artifact cannot be found at the path. |
| `SchemaValidationError` | An artifact or input payload fails internal schema validation. |
| `UnknownSkillError` | A skill ID is not present in `skills.json` (68 canonical skills). |
| `UnknownStudentError` | A student ID does not exist in student profile datasets. |
| `UnknownRoleError` | A role ID does not exist in role context definitions. |

---

## 6. Zero Black-Box Guarantee & Determinism

- **No Black-Box Scoring**: The ML service never computes opaque composite percentages, fit scores, or employability rankings.
- **Strict Determinism**: For any identical set of inputs, `MLService` returns byte-identical responses.
- **Zero Hallucination / Zero LLM Dependency**: All extraction and recommendation pipelines are deterministic rule-based algorithms with explicit evidence provenance.

---

## 7. Package Dependencies

The ML package requires ONLY standard data science dependencies:
- Python $\ge$ 3.10
- `numpy`
- `regex`

It does **NOT** require or install:
- `fastapi`, `uvicorn`, `starlette`
- `sqlalchemy`, `psycopg`, `alembic`
- `requests`, `httpx`, `urllib3`
