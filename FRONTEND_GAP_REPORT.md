# WorkNexus Frontend Gap Report

**Date**: September 22, 2026  
**Auditor**: Senior Staff Frontend Engineer & Product Reviewer  
**Scope**: Full UI/UX, Component Tree, API Integration, and Architecture Compliance Audit  
**Status**: AUDITED & REMEDIATION SPECIFIED  

---

## 1. Executive Summary

The WorkNexus frontend was developed as an early Hackathon demonstration using React 19, TypeScript, and Tailwind CSS. While it presents a polished visual theme with multilingual support, an audit of the client application reveals critical architectural discrepancies, a total disconnect from the backend REST API, client-side ML logic duplication, and missing portals for 3 out of 5 primary platform personas.

---

## 2. Comprehensive Gap Analysis Matrix

| Domain | Issue / Gap Identified | Severity | Impact | Required Remediation |
|---|---|---|---|---|
| **API Integration** | **Zero Network Calls (`fetch`/`axios`)**: UI reads exclusively from `mockDb.ts`. | **Critical** | Frontend is completely decoupled from FastAPI backend and database. | Implement centralized API client (`src/api/`) connecting to all `/api/v1/*` endpoints. |
| **Authentication & RBAC** | **Simulated Login**: `LoginPage.tsx` simulates auth with `setTimeout` and fake persona switching. | **Critical** | No real JWT tokens acquired, stored, or attached to requests. | Implement `AuthContext` with `/api/v1/auth/login`, `/api/v1/auth/me`, token storage, and logout. |
| **Persona Coverage** | **Missing 3 of 5 Roles**: Only 'admin', 'employer', and 'guest' exist in `types.ts`. | **High** | `Student`, `Institute`, and `Trainer` have no dedicated portals or navigation. | Expand `Role` type to `Admin`, `Institute`, `Employer`, `Trainer`, `Student` and provide dedicated views. |
| **Architecture Violation** | **Client-side ML Algorithm**: `skillGapAlgorithm.ts` computes gaps, alignment scores, and recommendations. | **High** | Violates requirement that frontend MUST NOT contain business or ML logic. | Remove `skillGapAlgorithm.ts`; bind `CourseDetail` to `/api/v1/ml/course-gaps` and `/api/v1/ml/students/.../gap/...`. |
| **Employer Workflow** | **In-memory Job Submissions**: `EmployerPortal.tsx` appends jobs to local React state. | **High** | No persistence; bypasses automatic ML skill extraction on job postings. | Connect form to `POST /api/v1/jobs/` and `POST /api/v1/employers/feedback`. |
| **Student Workflows** | **Missing Student Portal**: No student profile, role targeting, evidence submission, or course recommendations. | **High** | Students cannot discover personalized career pathways or course candidates. | Build `StudentPortal.tsx` consuming `/api/v1/roles`, `/api/v1/students/*`, and `/api/v1/ml/students/*`. |
| **Institute Workflows** | **Missing Institute Portal**: Institutes cannot map courses or review automated curriculum alignment. | **High** | Institutes cannot audit vocational curriculum gaps against industry demand. | Build `InstitutePortal.tsx` consuming `/api/v1/courses/` and `/api/v1/ml/course-gaps`. |
| **Trainer Workflows** | **Missing Trainer Hub**: Trainers have no view of emerging skill demand or evidence. | **Medium** | Faculty cannot tailor classroom instruction to market signals. | Build `TrainerHub.tsx` consuming `/api/v1/ml/demand` and `/api/v1/ml/evidence`. |
| **Admin Dashboard** | **Static Charts & Mock Metrics**: `AdminDashboard.tsx` displays hardcoded figures. | **Medium** | Government officials cannot inspect live ML demand intelligence or multi-signal evidence. | Integrate `/api/v1/ml/demand`, `/api/v1/ml/evidence`, and `/api/v1/ml/recommendations` with live/benchmark toggle. |
| **Legacy Artifacts** | **Lingering Flask Prototype (`SkillMesh/`)**: Legacy SQLite app embedded in `frontend/`. | **Medium** | Bloats repository and confuses developer onboarding. | Remove `frontend/SkillMesh` and `PythonProjectModal.tsx`. |
| **UX & Loading States** | **Missing Async States**: No loading spinners or error banners for server requests. | **Medium** | Poor user feedback during network operations. | Add loading skeletons and error banners across all asynchronous data views. |

---

## 3. Detailed Component-Level Audit

### 3.1 `LoginPage.tsx`
- **Current Behavior**:
  - Contains tabs for Admin, Employer, Trainee.
  - On submit, sets `isLoading(true)`, calls `setTimeout(..., 500)`, sets hardcoded role state, and redirects to static pages.
  - No call to `POST /api/v1/auth/login`.
- **Fix**:
  - Wire to `authApi.login({ email, password })`.
  - Store JWT `access_token` and `refresh_token`.
  - Provide real credentials pre-fill or registration link with proper error messages on 401/400.

### 3.2 `EmployerPortal.tsx` & `EmployerResponses.tsx`
- **Current Behavior**:
  - Form collects job details and employer comments.
  - Submits to parent callback `onSubmitJob` which updates an in-memory `responses` array initialized from `INITIAL_JOBS`.
  - Does not trigger ML skill extraction.
- **Fix**:
  - Connect to `POST /api/v1/jobs/` (extracts skills automatically) and `POST /api/v1/employers/feedback`.
  - Display the ML-extracted canonical skills returned from the backend in real time.

### 3.3 `CourseDetail.tsx` & `AdminDashboard.tsx`
- **Current Behavior**:
  - Invokes `calculateCourseSkillGap` locally on `INITIAL_COURSE_SKILLS` and `INITIAL_SKILL_DEMANDS`.
  - Displays Chart.js bar charts with static numbers.
- **Fix**:
  - Replace local calculations with `GET /api/v1/ml/course-gaps?mode=live`.
  - Display actual backend alignment score, identified gaps, and ML recommendations.

### 3.4 Missing Dedicated Role Portals
- **Student Portal (`StudentPortal.tsx`)**:
  - Target role selection dropdown (`GET /api/v1/roles/`).
  - Student skill profile and evidence history (`GET /api/v1/students/{id}/profile`, `GET /api/v1/students/{id}/evidence`).
  - Evidence submission modal (`POST /api/v1/students/{id}/evidence`).
  - Live Student Gap Visualizer (`GET /api/v1/ml/students/{id}/gap/{role_id}`).
  - Personalized recommendations and candidate courses (`GET /api/v1/ml/students/{id}/recommendations/{role_id}`, `GET /api/v1/ml/students/{id}/course-candidates/{role_id}`).
- **Institute Portal (`InstitutePortal.tsx`)**:
  - Course catalog management (`GET /api/v1/courses/`).
  - Curriculum gap overview with severity badges from ML (`GET /api/v1/ml/course-gaps`).
- **Trainer Hub (`TrainerHub.tsx`)**:
  - Industry demand breakdown (`GET /api/v1/ml/demand`).
  - Multi-signal evidence synthesis (`GET /api/v1/ml/evidence`).

---

## 4. Frontend Architecture Plan

```text
frontend/src/
├── api/
│   ├── client.ts              # Base fetch client with auth token headers & error parsing
│   ├── authApi.ts             # /api/v1/auth/login, register, me, logout
│   ├── jobsApi.ts             # /api/v1/jobs/, job-skills
│   ├── employersApi.ts        # /api/v1/employers/feedback
│   ├── rolesApi.ts            # /api/v1/roles/
│   ├── studentsApi.ts         # /api/v1/students/
│   ├── coursesApi.ts          # /api/v1/courses/
│   └── mlApi.ts               # /api/v1/ml/* (demand, gaps, evidence, recs, candidate courses)
├── context/
│   └── AuthContext.tsx        # React Auth Context for JWT session and active role
├── components/
│   ├── Header.tsx             # Role navigation header with live role switching & logout
│   ├── LandingPage.tsx        # Public landing overview
│   ├── LoginPage.tsx          # Real authenticated login
│   ├── AdminDashboard.tsx     # Government intelligence dashboard (live ML demand & gaps)
│   ├── StudentPortal.tsx      # Student career pathways, gap analysis, & course candidates
│   ├── InstitutePortal.tsx    # Institute curriculum gap management
│   ├── TrainerHub.tsx         # Trainer industry demand & multi-signal evidence
│   ├── EmployerPortal.tsx     # Real job posting & feedback submission with live ML extraction
│   ├── CourseDetail.tsx       # Backend-powered course alignment view
│   ├── EmergingSkills.tsx     # ML demand intelligence explorer
│   └── HelpModal.tsx          # Multilingual accessibility modal
```
