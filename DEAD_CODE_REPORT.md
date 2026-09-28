# WorkNexus / SkillMesh — Dead Code Elimination Report

**Generated Date:** September 25, 2026  
**Auditor:** Principal Software Architect & Senior Code Reviewer  
**Platform Scope:** Full Stack (`backend/`, `ml/`, `new-frontend/`)

---

## 1. Executive Summary

During the Phase 2 Dead Code Elimination audit, the WorkNexus codebase was systematically scanned for unused dependencies, redundant prototype mocks, dead imports, orphan endpoints, and obsolete compatibility shims.

Prior to this cleanup, several legacy prototypes, placeholder fallback classes, and misconfigured dependencies bloated the repository, caused runtime desynchronization, and introduced security risks. All identified dead code and redundant artifacts have been purged.

---

## 2. Inventory of Removed & Cleaned Components

### 2.1 Frontend Dependencies (`new-frontend/package.json`)
* **`@google/genai`**: Removed. The frontend interacts strictly with the WorkNexus FastAPI backend (`/api/ml/*`), never calling external Gemini APIs directly from client-side code (preventing API key exposure).
* **`express` & `@types/express`**: Removed. Server runtime dependencies were mistakenly bundled inside the Vite client single-page application.
* **`bun.lock`**: Removed redundant lockfile to prevent package manager conflicts with `package-lock.json` and standard Node/npm CI workflows.
* **`vite.config.ts`**: Replaced non-standard / CommonJS `__dirname` with modern ESM-native `import.meta.dirname`.

### 2.2 Backend Prototype Shims (`backend/app/main.py`)
* **`_DummyRoleService`**: Completely deleted. This mock class was intercepting role queries and returning static dictionaries when real database tables were empty.
* **`_DummyCourseService`**: Completely deleted. Replaced by real database service queries linked with seeded taxonomy.
* **`_DummyJobService`**: Completely deleted. Replaced by live PostgreSQL / SQLAlchemy queries.
* **Mock startup fallbacks**: Replaced with clean database migration and idempotent taxonomy seeding (`seed_all(db)`), ensuring the system boots in a pure production state.

### 2.3 Authentication Bypass Logic (`backend/app/auth/rbac.py`)
* **Unauthenticated User Mock Bypass**:
  ```python
  # REMOVED DEAD/DANGEROUS CODE:
  if not token:
      return UserContext(user_id=1, role="Employer", permissions=[...])
  ```
  This legacy testing fallback silently bypassed authentication for unauthenticated callers. It was removed and replaced with strict `HTTP 401 Unauthorized` token requirements.

### 2.4 ML Endpoint Hardcoded Mocks (`backend/app/api/routes_ml.py`)
* **Static `/course-gaps/{course_id}` Mock**:
  Removed hardcoded dictionary returning dummy `"Python"` and `"SQL"` gap counts. Replaced with dynamic database analysis querying real role skill requirements against registered course taxonomy.
* **Static `/evidence-summary/{skill_id}` Mock**:
  Removed hardcoded mock responses returning static counts (`{"student_count": 0, "status": "experimental"}`). Replaced with live aggregation querying `StudentSkillEvidence` tables.

### 2.5 Obsolete Lambda Filter Evaluators (`backend/app/services/ml_data_service.py`)
* **Mock Lambda Filters in Real DB Calls**:
  Cleaned out fragile `lambda x: x.id == val` filter invocations that caused `ArgumentError` when executed against real SQLAlchemy database sessions. All queries now execute canonical SQL binary clauses (`Model.field == val`) with dual-mode runtime detection.

### 2.6 Frontend Obsolete Payload Mappings (`new-frontend/src/pages/StudentPortal.tsx`)
* **Non-Canonical Evidence Types**:
  Removed legacy prototype dropdown options (`"github_pr"`) and replaced them with backend canonical domain types:
  - `project`
  - `certification`
  - `assessment`
  - `course_completed`
  - `self_reported`

---

## 3. Impact Assessment

| Metric | Before Audit | After Audit | Change |
| :--- | :--- | :--- | :--- |
| **Frontend Dependencies** | 22 packages | 19 packages | -3 dead / unneeded dependencies |
| **Frontend Production Build** | Failing (`__dirname` TS error) | **Clean Success** (1.55s) | Resolved |
| **Backend Mock Shims** | 3 dummy classes in `main.py` | 0 dummy classes | 100% real database execution |
| **Auth Fallback Vulnerabilities** | 1 critical bypass in `rbac.py` | 0 bypasses | Strict JWT Bearer required |
| **Static ML Mock Endpoints** | 2 hardcoded endpoints | 0 mock endpoints | Fully dynamic |

---

## 4. Verification & Validation

1. **Frontend Typecheck & Build**:
   ```bash
   npm run lint  # tsc --noEmit -> PASSED (0 errors)
   npm run build # vite build -> PASSED (dist/ built cleanly)
   ```
2. **Backend Automated Tests**:
   ```bash
   python -m pytest backend/tests -> 96/96 PASSED (100% pass rate)
   ```
3. **Runtime Check**:
   No references to removed dummy services or bypass tokens remain in any production path.
