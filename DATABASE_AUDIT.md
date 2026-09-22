# WorkNexus Database Architecture & Schema Audit Report

**Date**: September 22, 2026  
**Auditor**: Senior Staff Database Architect & DevOps Engineer  
**Scope**: Relational Schema, SQLAlchemy 2.0 ORM Models, Foreign Keys, Indexes, Constraints, and Alembic Migrations  
**Status**: AUDITED & FULLY COMPLIANT  

---

## 1. Executive Summary

The WorkNexus relational database layer was reviewed across PostgreSQL 15+ specifications and SQLite local development environments. The schema comprises 13 tables structuring users, authentication token lifecycles, skills taxonomies, curriculum courses, course-skill alignments, user-acquired proficiencies, job postings, job requirements, target career roles, role-skill specifications, student profiles, and multi-source skill evidence.

All foreign keys enforce appropriate referential integrity (`ON DELETE CASCADE` / `ON DELETE SET NULL`), unique constraints prevent duplicate association pairs, composite indexes accelerate foreign key joins, and the Alembic version tree forms a single deterministic linear graph.

---

## 2. Table-by-Table Verification Matrix

| Table Name | Primary Key | Key Foreign Keys | Unique Constraints | Indexes Defined | Cascade Behavior | Status |
|---|---|---|---|---|---|---|
| `users` | `id` (Int, PK) | None | `email` | `email` | N/A | ✅ Verified |
| `skills` | `id` (Int, PK) | None | `skill_id` (e.g. `SK_PYTHON`) | `skill_id`, `name`, `category` | Referenced by 5 tables | ✅ Verified |
| `courses` | `id` (Int, PK) | None | `course_id` | `course_id`, `name`, `department` | Referenced by `course_skills` | ✅ Verified |
| `course_skills` | `id` (Int, PK) | `course_id` -> `courses.id`, `skill_id` -> `skills.id` | `(course_id, skill_id)` | `course_id`, `skill_id` | `ON DELETE CASCADE` | ✅ Verified |
| `user_skills` | `id` (Int, PK) | `user_id` -> `users.id`, `skill_id` -> `skills.id` | `(user_id, skill_id)` | `user_id`, `skill_id` | `ON DELETE CASCADE` | ✅ Verified |
| `job_postings` | `id` (Int, PK) | None | None | `title`, `company_name`, `posted_date` | Referenced by `job_skills` | ✅ Verified |
| `job_skills` | `id` (Int, PK) | `job_id` -> `job_postings.id`, `skill_id` -> `skills.skill_id` | `(job_id, skill_id)` | `job_id`, `skill_id` | `ON DELETE CASCADE` | ✅ Verified |
| `refresh_tokens` | `id` (Int, PK) | `user_id` -> `users.id` | `token` | `token`, `user_id` | `ON DELETE CASCADE` | ✅ Verified |
| `target_roles` | `id` (Str, PK) | None | `id` (PK) | Primary Key | Referenced by `role_skills`, `student_profiles` | ✅ Verified |
| `role_skills` | `id` (Int, PK) | `role_id` -> `target_roles.id`, `skill_id` -> `skills.id` | `(role_id, skill_id)` | `role_id`, `skill_id` | `ON DELETE CASCADE` | ✅ Verified |
| `student_profiles` | `id` (Int, PK) | `user_id` -> `users.id`, `target_role_id` -> `target_roles.id` | `user_id` (One-to-One) | `user_id`, `target_role_id` | `ON DELETE CASCADE` (User), `SET NULL` (Role) | ✅ Verified |
| `student_skill_evidence` | `id` (Int, PK) | `student_profile_id` -> `student_profiles.id`, `skill_id` -> `skills.id` | None | `student_profile_id`, `skill_id` | `ON DELETE CASCADE` | ✅ Verified |

---

## 3. Alembic Migration Lineage Verification

The Alembic revision tree was inspected and repaired to eliminate multiple roots:

```text
[f97f51981d4c] create users table
       │
       ▼
[0507cf69fd83] create skills table
       │
       ▼
[861649acb717] create courses, user_skills, course_skills, refresh_tokens
       │
       ▼
[49ecdd8f4657] create job_postings and job_skills
       │
       ▼
[001_phase10] create target_roles, role_skills, student_profiles, student_skill_evidence
```

- **Branch Count**: 0 (Clean Linear History)
- **Head Revision**: `001_phase10`
- **Downgrade Support**: All revision scripts implement balanced `downgrade()` functions dropping tables and constraints in reverse topological order.

---

## 4. Query Optimization & Indexing Assessment

1. **Foreign Key Lookups**:
   - Every foreign key column in association tables (`job_skills.job_id`, `job_skills.skill_id`, `course_skills.course_id`, `course_skills.skill_id`, `user_skills.user_id`, `role_skills.role_id`, `student_profiles.user_id`, `student_skill_evidence.student_profile_id`) is explicitly indexed with `index=True`.
   - Eliminates table scans during JOIN operations and relational traversals.
2. **Text Search Optimization**:
   - `job_postings.title` and `job_postings.company_name` are indexed for fast pattern-matching and filtering.
3. **Temporal Sorting**:
   - `job_postings.posted_date` and `refresh_tokens.expires_at` are indexed for time-range filtering and expiry sweeps.
