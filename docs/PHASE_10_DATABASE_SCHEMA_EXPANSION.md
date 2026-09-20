# PHASE 10 — STUDENT & CAREER ROLE DATABASE FOUNDATION
===================================================================
**Project:** WorkNexus / SkillMesh (Smart India Hackathon 2026)  
**Branch:** `ml-dev`  
**Status:** COMPLETE & VERIFIED (323/323 Total Tests Passing)  
**Execution Date:** September 2026  

---

## 1. Executive Summary & Objective

Phase 10 implements the **normalized database foundation** for career role requirements and student skill evidence.

Prior to Phase 10, the backend database supported jobs, job skills, employers, employer feedback, and courses, but lacked relational models for career target roles and student skill evidence. Consequently, operations 8–12 (`get_role_skill_context`, `get_student_skill_profile`, `get_student_skill_gap`, `get_personalized_recommendations`, `get_course_candidates`) were categorized as `BLOCKED_BY_MISSING_BACKEND_DATA` in live mode.

Phase 10 introduces the minimum normalized backend data schema required to unblock live student and career role intelligence for Phase 10B without modifying ML algorithms or duplicating identity tables.

### Key Architectural Invariants Enforced
- **Zero Identity Duplication**: `StudentProfile` extends existing `User(role="Student")` records via foreign key; no second auth identity is created.
- **Single Canonical Taxonomy**: `RoleSkill` and `StudentSkillEvidence` reference the authoritative `Skill(id)` table (`SK_*`).
- **Categorical Evidence Integrity**: Skill evidence types (`self_reported`, `course_completed`, `project`, `certification`, `assessment`) and strength categories (`basic`, `intermediate`, `advanced`) are stored as clean categorical domains without conversion into arbitrary numerical proficiency scores.
- **Multiple Evidence Records Supported**: Students can legitimately hold multiple distinct evidence records for the same skill (e.g. `project + intermediate` and `certification + advanced`).
- **Zero Database Contamination in ML**: ML engine remains 100% database-agnostic with zero imports of SQLAlchemy, migrations, or FastAPI.

---

## 2. Entity Schema & Relationship Architecture

```
┌────────────────────────────────────────────────────────┐
│                        User                            │
│  id: Integer (PK)                                      │
│  email: String                                         │
│  role: String ("Student", "Employer", "Admin", etc.)   │
│  is_active: Boolean                                    │
└───────────────────────────┬────────────────────────────┘
                            │ 1:1 (role="Student")
                            ▼
┌────────────────────────────────────────────────────────┐       ┌────────────────────────────────────────────────────────┐
│                   StudentProfile                       │       │                      TargetRole                        │
│  id: Integer (PK)                                      │       │  id: String (PK, e.g. "ROLE_DATA_ENGINEER")            │
│  user_id: Integer (FK -> users.id, UNIQUE)             │──────▶│  name: String                                          │
│  target_role_id: String (FK -> target_roles.id, NULL)  │       │  description: Text                                     │
│  created_at: DateTime(UTC)                             │       │  is_active: Boolean                                    │
└───────────────────────────┬────────────────────────────┘       │  created_at: DateTime(UTC)                             │
                            │                                    └───────────────────────────┬────────────────────────────┘
                            │ 1:N                                                            │ 1:N
                            ▼                                                                ▼
┌────────────────────────────────────────────────────────┐       ┌────────────────────────────────────────────────────────┐
│                StudentSkillEvidence                    │       │                       RoleSkill                        │
│  id: Integer (PK)                                      │       │  id: Integer (PK)                                      │
│  student_profile_id: Integer (FK -> student_profiles)  │       │  role_id: String (FK -> target_roles.id)               │
│  skill_id: String (FK -> skills.id)                    │───┐   │  skill_id: String (FK -> skills.id)                    │───┐
│  evidence_type: String (Enum)                          │   │   │  created_at: DateTime(UTC)                             │   │
│  strength: String (Enum)                               │   │   │  UNIQUE(role_id, skill_id)                             │   │
│  metadata: JSON                                        │   │   └────────────────────────────────────────────────────────┘   │
│  created_at: DateTime(UTC)                             │   │                                                                │
└────────────────────────────────────────────────────────┘   │                                                                │
                                                             │                                                                │
                                                             ▼                                                                ▼
                                              ┌────────────────────────────────────────────────────────┐
                                              │                         Skill                          │
                                              │  id: String (PK, e.g. "SK_PYTHON")                     │
                                              │  name: String                                          │
                                              │  category: String                                      │
                                              │  version: Integer                                      │
                                              └────────────────────────────────────────────────────────┘
```

---

## 3. Database Migration & Table Specifications

Alembic migration `001_phase10_student_role_schema.py` defines:

### 1. `target_roles` Table
- `id` (VARCHAR(64), Primary Key): Standard ML role ID (e.g. `ROLE_DATA_ENGINEER`).
- `name` (VARCHAR(128), NOT NULL): Human-readable role title.
- `description` (TEXT, NULL): Role scope and responsibilities.
- `is_active` (BOOLEAN, DEFAULT True): Status flag.
- `created_at` (DATETIME with timezone, NOT NULL): UTC creation timestamp.

### 2. `role_skills` Table
- `id` (INTEGER, Primary Key, Auto-increment).
- `role_id` (VARCHAR(64), FK $	o$ `target_roles.id` ON DELETE CASCADE).
- `skill_id` (VARCHAR(64), FK $	o$ `skills.id` ON DELETE CASCADE).
- `created_at` (DATETIME with timezone, NOT NULL).
- **Constraints**: `UNIQUE(role_id, skill_id)` to prevent duplicate mappings.
- **Indexes**: `ix_role_skills_role_id`, `ix_role_skills_skill_id`.

### 3. `student_profiles` Table
- `id` (INTEGER, Primary Key, Auto-increment).
- `user_id` (INTEGER, FK $	o$ `users.id` ON DELETE CASCADE, UNIQUE).
- `target_role_id` (VARCHAR(64), FK $	o$ `target_roles.id` ON DELETE SET NULL, NULL).
- `created_at` (DATETIME with timezone, NOT NULL).
- **Indexes**: `ix_student_profiles_user_id`, `ix_student_profiles_target_role_id`.

### 4. `student_skill_evidence` Table
- `id` (INTEGER, Primary Key, Auto-increment).
- `student_profile_id` (INTEGER, FK $	o$ `student_profiles.id` ON DELETE CASCADE).
- `skill_id` (VARCHAR(64), FK $	o$ `skills.id` ON DELETE CASCADE).
- `evidence_type` (VARCHAR(32), NOT NULL): `self_reported`, `course_completed`, `project`, `certification`, `assessment`.
- `strength` (VARCHAR(16), NOT NULL): `basic`, `intermediate`, `advanced`.
- `metadata` (JSON, NULL): Contextual details (repository URL, certificate title, exam score).
- `created_at` (DATETIME with timezone, NOT NULL).
- **Indexes**: `ix_student_skill_evidence_profile_id`, `ix_student_skill_evidence_skill_id`.

---

## 4. Benchmark Seed Strategy & Demo Separation

`backend/app/db/seed.py` implements deterministic seeding:

### A. Canonical Skill Seeding (`seed_canonical_skills`)
- Seeds all 68 canonical skills from `ml/data/skills.json` into the `skills` table.

### B. Benchmark Career Role Seeding (`seed_benchmark_roles`)
- Seeds the 5 synthetic benchmark target roles and their 26 exact Phase 6B required skill mappings:
  1. `ROLE_DATA_ENGINEER` (5 skills): Python, SQL, Airflow, Spark, AWS.
  2. `ROLE_EV_TECHNICIAN` (6 skills): BMS, CAN, Battery Cell, DIAG, High Voltage, THERMAL.
  3. `ROLE_FULL_STACK_DEV` (6 skills): Python, JavaScript, React, SQL, Git, Docker.
  4. `ROLE_HEALTHCARE_ASST` (5 skills): CPR_BLS, FIRST_AID, Patient Care, Vital Signs, EHR.
  5. `ROLE_INDUSTRIAL_AUTO` (4 skills): PLC, SCADA, Panel Wiring, Circuit Design.
- **Documentation Note**: Labeled explicitly as benchmark demonstration data.

### C. Demo Student Profile Seeding (`seed_demo_students`)
- Provides an isolated seed utility for synthetic benchmark students `STU_001` through `STU_005` and their multi-source skill evidence.
- Fully separated from production user provisioning.

---

## 5. API Surface & Data Access Services

### Services
- **`RoleService`** (`backend/app/services/role_service.py`): Target role creation, role retrieval, role listing, and role-skill association management.
- **`StudentService`** (`backend/app/services/student_service.py`): Student profile retrieval, target role assignment, and skill evidence ingestion.

### Endpoints (RBAC Enforced)
| Endpoint | Method | Allowed Roles | Description | Response Model |
| :--- | :---: | :---: | :--- | :--- |
| `/api/v1/roles/` | `GET` | All (Authenticated) | List all active target career roles | `List[TargetRoleResponseSchema]` |
| `/api/v1/roles/{role_id}` | `GET` | All (Authenticated) | Retrieve target role and its required skills | `TargetRoleResponseSchema` |
| `/api/v1/roles/` | `POST` | `Admin` | Create a new target career role with required skills | `TargetRoleResponseSchema` |
| `/api/v1/students/{user_id}/profile` | `GET` | Self, `Institute`, `Admin` | Retrieve student profile and evidence records | `StudentProfileResponseSchema` |
| `/api/v1/students/{user_id}/evidence` | `POST` | Self, `Institute`, `Admin` | Ingest a new skill evidence record | `StudentSkillEvidenceResponseSchema` |
| `/api/v1/students/{user_id}/evidence` | `GET` | Self, `Institute`, `Admin` | List all skill evidence records for student | `List[StudentSkillEvidenceResponseSchema]` |

---

## 6. Verification & Test Suite Execution

### Summary of Tests Run (323 Tests Passing)
```bash
# Run All Backend Tests (33 tests)
python -m unittest discover -s backend/tests -p "test_*.py"

# Run All ML Tests (290 tests)
python -m unittest discover -s ml -p "test_*.py"
```

| Component | Test File | Test Count | Result |
| :--- | :--- | :---: | :---: |
| **Phase 10 Database Foundation** | `backend/tests/test_phase10_database.py` | 10 | PASS |
| **Live Intelligence Integration** | `backend/tests/test_live_intelligence.py` | 7 | PASS |
| **Backend Routes & RBAC** | `backend/tests/test_routes.py` | 10 | PASS |
| **Backend ML Adapter** | `backend/tests/test_ml_adapter.py` | 4 | PASS |
| **Backend Job Integration** | `backend/tests/test_job_integration.py` | 1 | PASS |
| **Backend Feedback Integration** | `backend/tests/test_employer_feedback_integration.py` | 1 | PASS |
| **ML Engine Tests (Phases 0.5 - 8)** | `ml/` (16 test suites) | 290 | PASS |
| **Total Test Suite** | **22 test modules** | **323** | **323 / 323 PASS** |

---

## 7. Known Limitations & Phase 10B Prerequisites

1. **Current Status**: Phase 10 establishes the relational database models, schemas, services, and migrations.
2. **Phase 10B Goal**: Connect `MLAdapter` and `MLService` to these live database models to promote:
   - `get_role_skill_context()` $	o$ `LIVE_READY`
   - `get_student_skill_profile()` $	o$ `LIVE_READY`
   - `get_student_skill_gap()` $	o$ `LIVE_READY`
   - `get_personalized_recommendations()` $	o$ `LIVE_READY`
   - `get_course_candidates()` $	o$ `LIVE_READY`
