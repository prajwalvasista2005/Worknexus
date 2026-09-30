# SkillMesh API Reference Documentation

> **Base URL:** `http://127.0.0.1:8000`  
> **API v1 Prefix:** `http://127.0.0.1:8000/api/v1`  
> **Interactive Documentation (Swagger UI):** `http://127.0.0.1:8000/docs`  
> **Alternative Documentation (ReDoc):** `http://127.0.0.1:8000/redoc`  
> **Current Version:** `1.0.0`  
> **Platform:** SkillMesh by WorkNexus (Labour Market Intelligence & Curriculum Alignment Platform)

---

## 1. Global Headers & Conventions

All endpoints adhere to RESTful HTTP semantics.

### Standard Request Headers
| Header | Required For | Format / Value | Description |
| :--- | :--- | :--- | :--- |
| `Content-Type` | `POST`, `PUT`, `PATCH` | `application/json` | Specifies JSON payload format. |
| `Accept` | All Requests | `application/json` | Requested response format. |
| `Authorization` | Protected Routes | `Bearer <access_token>` | OAuth2 Bearer token obtained from `/auth/login` or `/api/v1/auth/login`. |
| `X-User-Id` | Role-Emulation / Dev | Integer (e.g. `1`) | Header-based user context identifier. |
| `X-User-Role` | Role-Emulation / Dev | String (`Admin`, `Institute`, `Employer`, `Trainer`, `Student`) | Header-based RBAC role context. |

---

## 2. JWT Authentication & Token Lifecycle

- **Algorithm:** `HS256`
- **Access Token Expiry:** 30 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- **Refresh Token Expiry:** 7 days (configurable via `REFRESH_TOKEN_EXPIRE_DAYS`)
- **Token Rotation:** Every call to `POST /auth/refresh` revokes the old refresh token in the database and issues a new access/refresh token pair.
- **Revocation / Logout:** `POST /auth/revoke` invalidates the active refresh token.

---

## 3. Core Authentication & Profile Endpoints

### 3.1 Register User
- **Route:** `POST /auth/register` (also `/api/v1/auth/register`)
- **Status:** `201 Created`
- **Request Body:**
  ```json
  {
    "email": "student@worknexus.org",
    "password": "StrongPassword123!",
    "full_name": "Aarav Sharma",
    "role": "student"
  }
  ```
- **Response Body (`201 Created`):**
  ```json
  {
    "id": 1,
    "email": "student@worknexus.org",
    "full_name": "Aarav Sharma",
    "role": "student",
    "is_active": true,
    "created_at": "2026-09-22T12:00:00Z"
  }
  ```

### 3.2 Login (JSON Credentials)
- **Route:** `POST /auth/login` (also `/api/v1/auth/login`)
- **Status:** `200 OK`
- **Request Body:**
  ```json
  {
    "email": "student@worknexus.org",
    "password": "StrongPassword123!"
  }
  ```
- **Response Body:**
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "token_type": "bearer"
  }
  ```

### 3.3 Get Current User Profile
- **Route:** `GET /auth/me` (also `/api/v1/auth/me`)
- **Status:** `200 OK`
- **Headers:** `Authorization: Bearer <access_token>`
- **Response Body:**
  ```json
  {
    "id": 1,
    "email": "student@worknexus.org",
    "full_name": "Aarav Sharma",
    "role": "student",
    "is_active": true,
    "created_at": "2026-09-22T12:00:00Z"
  }
  ```

### 3.4 Rotate Refresh Token
- **Route:** `POST /auth/refresh` (also `/api/v1/auth/refresh`)
- **Status:** `200 OK`
- **Request Body:**
  ```json
  {
    "refresh_token": "eyJhbGciOi..."
  }
  ```
- **Response Body:**
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "token_type": "bearer"
  }
  ```

---

## 4. Skills Taxonomy & Curriculum Courses

### 4.1 List Skills
- **Route:** `GET /skills/` (also `/api/v1/skills/`)
- **Query Params:** `category`, `is_active`
- **Response:** List of `SkillResponse` (`id`, `skill_id`, `name`, `category`, `is_active`, `created_at`).

### 4.2 List Curriculum Courses
- **Route:** `GET /courses/` (also `/api/v1/courses/`)
- **Query Params:** `department`, `is_active`, `skip`, `limit`
- **Response:** List of `CourseResponse` (`id`, `course_id`, `name`, `department`, `semester`, `is_active`).

### 4.3 Get Course Skills Mapping
- **Route:** `GET /courses/{id}/skills` (also `/api/v1/courses/{id}/skills`)
- **Response:** List of `CourseSkillResponse` (`id`, `course_id`, `skill_id`, `coverage_percentage`).

---

## 5. Job Intake & Automated ML Skill Extraction

### 5.1 Create Job Posting (with ML Extraction)
- **Route:** `POST /api/v1/jobs/`
- **RBAC:** `Employer`, `Admin`
- **Status:** `201 Created`
- **Request Body:**
  ```json
  {
    "title": "Full Stack Cloud Developer",
    "company": "Tata Motors",
    "location": "Pune",
    "description": "Seeking engineer skilled in Python, FastAPI, Docker, and SQL.",
    "employer_id": 1
  }
  ```
- **Response Body (`201 Created`):**
  ```json
  {
    "id": 1,
    "title": "Full Stack Cloud Developer",
    "company": "Tata Motors",
    "location": "Pune",
    "description": "Seeking engineer skilled in Python, FastAPI, Docker, and SQL.",
    "employer_id": 1,
    "extracted_skills": [
      { "skill_id": "SK_PYTHON", "confidence_score": 0.98 },
      { "skill_id": "SK_FASTAPI", "confidence_score": 0.97 },
      { "skill_id": "SK_DOCKER", "confidence_score": 0.95 },
      { "skill_id": "SK_SQL", "confidence_score": 0.94 }
    ],
    "created_at": "2026-09-22T12:05:00Z"
  }
  ```

### 5.2 List Job Postings
- **Route:** `GET /api/v1/jobs/`
- **Response:** List of `JobResponseSchema`.

---

## 6. Employer Feedback & Qualitative Signal Detection

### 6.1 Submit Feedback
- **Route:** `POST /api/v1/employers/feedback`
- **RBAC:** `Employer`, `Admin`
- **Status:** `201 Created`
- **Request Body:**
  ```json
  {
    "employer_id": 1,
    "course_id": 101,
    "comments": "Graduates demonstrate good fundamentals but lack practical Docker containerization and CAN bus diagnostics.",
    "rating": 4
  }
  ```
- **Response Body (`201 Created`):**
  ```json
  {
    "id": 1,
    "employer_id": 1,
    "course_id": 101,
    "comments": "...",
    "rating": 4,
    "signals": [
      {
        "skill_id": "SK_DOCKER",
        "confidence_score": 0.96,
        "trust_weight": 1.0,
        "weighted_signal": 0.96
      },
      {
        "skill_id": "SK_CAN",
        "confidence_score": 0.94,
        "trust_weight": 1.0,
        "weighted_signal": 0.94
      }
    ],
    "created_at": "2026-09-22T12:10:00Z"
  }
  ```

---

## 7. Career Target Roles & Student Profiles

### 7.1 List Target Roles
- **Route:** `GET /api/v1/roles/`
- **Response:** List of `TargetRoleResponseSchema` (`id`, `name`, `description`, `is_active`, `required_skills`).

### 7.2 Get Target Role Detail
- **Route:** `GET /api/v1/roles/{role_id}`
- **Response:** `TargetRoleResponseSchema`.

### 7.3 Get Student Profile
- **Route:** `GET /api/v1/students/{user_id}/profile`
- **RBAC:** `Student` (own), `Institute`, `Admin`
- **Response:** `StudentProfileResponseSchema` (`id`, `user_id`, `target_role_id`, `evidence_records`, `created_at`).

### 7.4 Submit Student Skill Evidence
- **Route:** `POST /api/v1/students/{user_id}/evidence`
- **Request Body:**
  ```json
  {
    "skill_id": "SK_PYTHON",
    "evidence_type": "project",
    "strength": "high",
    "metadata": {
      "repo_url": "https://github.com/student/worknexus-project",
      "verified_by": "Dr. Suresh Patil"
    }
  }
  ```
- **Response:** `StudentSkillEvidenceResponseSchema`.

---

## 8. ML Intelligence Engine Endpoints

| Endpoint | Method | Query Parameters | Description |
|---|---|---|---|
| `/api/v1/ml/extract-skills` | `POST` | None | Extract canonical skills from arbitrary free text (`{ "text": "..." }`). |
| `/api/v1/ml/demand` | `GET` | `mode=live\|benchmark` | Macro labour market skill demand ranking and growth rates. |
| `/api/v1/ml/course-gaps` | `GET` | `mode=live\|benchmark` | Curriculum course-skill gap analysis, coverage gaps, and recommendations. |
| `/api/v1/ml/evidence` | `GET` | `mode=live\|benchmark` | Multi-signal synthesized evidence across industry demand, curriculum, and feedback. |
| `/api/v1/ml/recommendations` | `GET` | `mode=live\|benchmark` | Prioritized skill policy and curriculum intervention recommendations. |
| `/api/v1/ml/roles/{role_id}` | `GET` | `mode=live\|benchmark` | Skill context, mandatory vs optional skills for a career target role. |
| `/api/v1/ml/students/{student_id}/profile` | `GET` | `mode=live\|benchmark` | Normalized student skill profile synthesized from multi-source evidence. |
| `/api/v1/ml/students/{student_id}/gap/{role_id}` | `GET` | `mode=live\|benchmark` | Student personal skill gap against the target career role. |
| `/api/v1/ml/students/{student_id}/recommendations/{role_id}` | `GET` | `mode=live\|benchmark` | Personalized skill acquisition recommendations for a student. |
| `/api/v1/ml/students/{student_id}/course-candidates/{role_id}` | `GET` | `mode=live\|benchmark` | Matching courses to bridge the student's personal skill gap for the role. |
