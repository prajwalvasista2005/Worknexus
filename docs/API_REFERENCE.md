# WorkNexus API Reference Documentation

> **Base URL:** `http://127.0.0.1:8000`  
> **Interactive Documentation (Swagger UI):** `http://127.0.0.1:8000/docs`  
> **Alternative Documentation (ReDoc):** `http://127.0.0.1:8000/redoc`  
> **Current Version:** `1.0.0`  
> **Platform:** WorkNexus (Labour Market Intelligence & Curriculum Alignment Platform)

---

## 1. Global Headers & Conventions

All endpoints follow standard RESTful HTTP semantics.

### Standard Request Headers
| Header | Required For | Format / Value | Description |
| :--- | :--- | :--- | :--- |
| `Content-Type` | `POST`, `PUT`, `PATCH` | `application/json` | Specifies JSON body payload. |
| `Accept` | All Requests | `application/json` | Informs server of accepted response format. |
| `Authorization` | Protected Routes | `Bearer <access_token>` | OAuth2 Bearer token obtained from `/auth/login` or `/auth/token`. |

### Standard Response Structure
- Successful requests return JSON objects or lists corresponding to defined Pydantic schemas.
- Error responses return a JSON object with a `detail` key:
  ```json
  {
    "detail": "Error description message"
  }
  ```

---

## 2. JWT Authentication & Token Lifecycle

WorkNexus secures private endpoints using signed JSON Web Tokens (JWT) adhering to RFC 7519.

### Token Specifications
- **Algorithm:** `HS256` (HMAC-SHA256)
- **Token Type:** `bearer`
- **Access Token Lifetime:** 30 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- **Refresh Token Lifetime:** 7 days (configurable via `REFRESH_TOKEN_EXPIRE_DAYS`)
- **Token Rotation:** Every call to `POST /auth/refresh` revokes the submitted refresh token in the database and issues a new access token paired with a newly rotated refresh token.
- **Revocation & Logout:** `POST /auth/logout` immediately invalidates the refresh token in PostgreSQL.

### Access Token Claims
```json
{
  "sub": "user@example.com",
  "role": "student",
  "user_id": 1,
  "type": "access",
  "jti": "550e8400-e29b-41d4-a716-446655440000",
  "iat": 1773449400,
  "exp": 1773451200
}
```

### Refresh Token Claims
```json
{
  "sub": "user@example.com",
  "user_id": 1,
  "type": "refresh",
  "jti": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "iat": 1773449400,
  "exp": 1774054200
}
```

---

## 3. System Health Check

### `GET /`
Returns the operational health status and platform metadata.

- **Authentication:** None
- **Request Body:** None
- **Response Body (`200 OK`):**
  ```json
  {
    "status": "healthy",
    "platform": "WorkNexus",
    "version": "1.0.0",
    "message": "WorkNexus Labour Market Intelligence API is up and running!"
  }
  ```

---

## 4. Authentication Endpoints

### 4.1 Register User
#### `POST /auth/register`
Creates a new user account, securely hashes password using bcrypt, and returns the profile details.

- **Authentication:** None
- **Status Code:** `201 Created`
- **Request Body (`UserCreate`):**
  ```json
  {
    "email": "student@example.com",
    "password": "SecurePassword123!",
    "full_name": "Prajwal Vasista",
    "role": "student"
  }
  ```
- **Response Body (`UserResponse`):**
  ```json
  {
    "id": 1,
    "email": "student@example.com",
    "full_name": "Prajwal Vasista",
    "role": "student",
    "is_active": true,
    "created_at": "2026-09-16T18:00:00Z"
  }
  ```
- **Possible Errors:**
  - `400 Bad Request`: Email already registered.
  - `422 Unprocessable Entity`: Password < 6 chars, invalid email format, or missing fields.

---

### 4.2 User Login (JSON)
#### `POST /auth/login`
Authenticates user credentials and returns an access token and refresh token.

- **Authentication:** None
- **Status Code:** `200 OK`
- **Request Body (`UserLogin`):**
  ```json
  {
    "email": "student@example.com",
    "password": "SecurePassword123!"
  }
  ```
- **Response Body (`Token`):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
  ```
- **Possible Errors:**
  - `401 Unauthorized`: Incorrect email or password (`WWW-Authenticate: Bearer`).
  - `400 Bad Request`: Inactive user account.
  - `422 Unprocessable Entity`: Missing email or password.

---

### 4.3 OAuth2 Form Login (Swagger UI)
#### `POST /auth/token`
Accepts `application/x-www-form-urlencoded` credentials (`username`, `password`) for Swagger UI authorization.

- **Authentication:** None
- **Status Code:** `200 OK`
- **Request Body:** Form data `username=<email>&password=<password>`
- **Response Body (`Token`):** Same as `POST /auth/login`.
- **Possible Errors:** `401 Unauthorized`, `400 Bad Request`.

---

### 4.4 Refresh Token (Token Rotation)
#### `POST /auth/refresh`
Rotates a valid refresh token, revoking the previous token and issuing a fresh access token and new refresh token.

- **Authentication:** None (requires valid `refresh_token` in body)
- **Status Code:** `200 OK`
- **Request Body (`TokenRefreshRequest`):**
  ```json
  {
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
  ```
- **Response Body (`Token`):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
  ```
- **Possible Errors:**
  - `401 Unauthorized`: Invalid, expired, or previously revoked refresh token.
  - `422 Unprocessable Entity`: Missing `refresh_token` field.

---

### 4.5 Logout (Token Revocation)
#### `POST /auth/logout`
Revokes the refresh token in PostgreSQL, terminating the active session.

- **Authentication:** None
- **Status Code:** `200 OK`
- **Request Body (`TokenRefreshRequest`):**
  ```json
  {
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
  ```
- **Response Body:**
  ```json
  {
    "message": "Successfully logged out"
  }
  ```
- **Possible Errors:**
  - `400 Bad Request`: Invalid or unknown refresh token.

---

### 4.6 Current User Profile
#### `GET /auth/me`
Retrieves authenticated user profile.

- **Authentication:** Required (`Authorization: Bearer <access_token>`)
- **Status Code:** `200 OK`
- **Request Body:** None
- **Response Body (`UserResponse`):**
  ```json
  {
    "id": 1,
    "email": "student@example.com",
    "full_name": "Prajwal Vasista",
    "role": "student",
    "is_active": true,
    "created_at": "2026-09-16T18:00:00Z"
  }
  ```
- **Possible Errors:**
  - `401 Unauthorized`: Missing, expired, or invalid bearer token.
  - `400 Bad Request`: Inactive account.

---

## 5. Skills Taxonomy Endpoints

### 5.1 List All Skills
#### `GET /skills/`
Retrieves all registered skills, with optional query filtering.

- **Authentication:** Optional
- **Query Parameters:**
  - `category` (string, optional): Filter by category (e.g. `IT & Software`)
  - `is_active` (boolean, optional): Filter active status (`true`/`false`)
- **Response Body (`200 OK`):**
  ```json
  [
    {
      "id": 1,
      "skill_id": "SKL-PY-01",
      "name": "Python",
      "category": "IT & Software",
      "description": "Python programming language for data & web",
      "is_active": true,
      "created_at": "2026-09-16T18:00:00Z"
    }
  ]
  ```

---

### 5.2 Get Skill by ID
#### `GET /skills/{skill_id}`
- **Authentication:** Optional
- **Path Parameter:** `skill_id` (integer)
- **Response Body (`200 OK`):** `SkillResponse` object.
- **Possible Errors:**
  - `404 Not Found`: Skill not found.

---

### 5.3 Create Skill
#### `POST /skills/`
Registers a new skill in the taxonomy.

- **Authentication:** Optional
- **Status Code:** `201 Created`
- **Request Body (`SkillCreate`):**
  ```json
  {
    "skill_id": "SKL-AI-01",
    "name": "Machine Learning Fundamentals",
    "category": "AI & Data Science",
    "description": "Supervised & unsupervised ML principles"
  }
  ```
- **Response Body (`SkillResponse`):** Created skill object.
- **Possible Errors:**
  - `400 Bad Request`: Skill code `skill_id` already exists.
  - `422 Unprocessable Entity`: Validation failure.

---

### 5.4 Update Skill
#### `PUT /skills/{skill_id}`
Updates details of an existing skill.

- **Authentication:** Optional
- **Path Parameter:** `skill_id` (integer)
- **Request Body (`SkillUpdate`):**
  ```json
  {
    "name": "Advanced Python & Microservices",
    "description": "Updated syllabus description",
    "is_active": true
  }
  ```
- **Response Body (`200 OK`):** Updated `SkillResponse`.
- **Possible Errors:** `404 Not Found`.

---

### 5.5 Delete Skill
#### `DELETE /skills/{skill_id}`
Permanently deletes a skill from the taxonomy.

- **Path Parameter:** `skill_id` (integer)
- **Response Body (`200 OK`):**
  ```json
  {
    "message": "Skill deleted successfully"
  }
  ```
- **Possible Errors:** `404 Not Found`.

---

## 6. Courses Endpoints

### 6.1 List Courses
#### `GET /courses/`
Lists curriculum courses with optional filtering and pagination.

- **Authentication:** Optional
- **Query Parameters:**
  - `department` (string, optional): Filter by department (e.g. `Computer Science`)
  - `is_active` (boolean, optional): Filter active courses
  - `skip` (integer, default `0`): Pagination offset
  - `limit` (integer, default `100`): Pagination limit
- **Response Body (`200 OK`):**
  ```json
  [
    {
      "id": 1,
      "course_id": "CRS-DS-101",
      "name": "Data Analytics & Business Intelligence",
      "description": "Comprehensive course covering SQL, Power BI, and Python",
      "department": "IT & Software",
      "semester": "Semester 1",
      "is_active": true,
      "created_at": "2026-09-16T18:00:00Z"
    }
  ]
  ```

---

### 6.2 Get Course by ID
#### `GET /courses/{id}`
- **Path Parameter:** `id` (integer)
- **Response Body (`200 OK`):** `CourseResponse` object.
- **Possible Errors:** `404 Not Found`.

---

### 6.3 Create Course
#### `POST /courses/`
Creates a curriculum course.

- **Status Code:** `201 Created`
- **Request Body (`CourseCreate`):**
  ```json
  {
    "course_id": "CRS-EV-201",
    "name": "Electric Vehicle Powertrain & Battery Tech",
    "description": "Vocational course for EV battery diagnostics",
    "department": "Automotive",
    "semester": "Term 2",
    "is_active": true
  }
  ```
- **Response Body (`CourseResponse`):** Created course object.
- **Possible Errors:**
  - `400 Bad Request`: `course_id` already exists.
  - `422 Unprocessable Entity`: Validation failure.

---

### 6.4 Update Course
#### `PUT /courses/{id}`
- **Path Parameter:** `id` (integer)
- **Request Body (`CourseUpdate`):**
  ```json
  {
    "name": "Advanced EV Powertrain Tech",
    "is_active": true
  }
  ```
- **Response Body (`200 OK`):** Updated `CourseResponse`.
- **Possible Errors:** `404 Not Found`.

---

### 6.5 Delete Course
#### `DELETE /courses/{id}`
- **Path Parameter:** `id` (integer)
- **Response Body (`200 OK`):** `{"message": "Course deleted successfully"}`.
- **Possible Errors:** `404 Not Found`.

---

### 6.6 Get Skills Taught by Course
#### `GET /courses/{id}/skills`
Retrieves all skills mapped to a course curriculum.

- **Path Parameter:** `id` (integer)
- **Response Body (`200 OK`):**
  ```json
  [
    {
      "id": 1,
      "course_id": 1,
      "skill_id": 5,
      "created_at": "2026-09-16T18:00:00Z"
    }
  ]
  ```
- **Possible Errors:** `404 Not Found`.

---

## 7. User Skills Endpoints

### 7.1 Get Current User Skills
#### `GET /user-skills/me`
Retrieves skills possessed by the currently authenticated user.

- **Authentication:** Required (`Bearer <access_token>`)
- **Response Body (`200 OK`):**
  ```json
  [
    {
      "id": 1,
      "user_id": 1,
      "skill_id": 5,
      "proficiency_level": "intermediate",
      "source": "assessment",
      "created_at": "2026-09-16T18:00:00Z"
    }
  ]
  ```
- **Possible Errors:** `401 Unauthorized`.

---

### 7.2 List User Skills
#### `GET /user-skills/`
Lists skills for a specified user (or current user if omitted).

- **Authentication:** Required (`Bearer <access_token>`)
- **Query Parameters:** `user_id` (integer, optional)
- **Response Body (`200 OK`):** List of `UserSkillResponse` items.

---

### 7.3 Add Skill to Profile
#### `POST /user-skills/`
Associates an acquired skill to the authenticated user's profile.

- **Authentication:** Required (`Bearer <access_token>`)
- **Status Code:** `201 Created`
- **Request Body (`UserSkillCreate`):**
  ```json
  {
    "skill_id": 5,
    "proficiency_level": "advanced",
    "source": "course_completion"
  }
  ```
- **Response Body (`UserSkillResponse`):** Created record.
- **Possible Errors:**
  - `404 Not Found`: Skill ID does not exist.
  - `400 Bad Request`: Skill already added to user profile.
  - `401 Unauthorized`: Not authenticated.

---

### 7.4 Update User Skill
#### `PUT /user-skills/{id}`
Updates proficiency level or source of a user skill.

- **Authentication:** Required (`Bearer <access_token>`)
- **Path Parameter:** `id` (integer)
- **Request Body (`UserSkillUpdate`):**
  ```json
  {
    "proficiency_level": "expert"
  }
  ```
- **Response Body (`200 OK`):** Updated `UserSkillResponse`.
- **Possible Errors:**
  - `404 Not Found`: Record not found.
  - `403 Forbidden`: Not authorized to edit another user's skill.

---

### 7.5 Delete User Skill
#### `DELETE /user-skills/{id}`
Removes a skill from the user's profile.

- **Authentication:** Required (`Bearer <access_token>`)
- **Path Parameter:** `id` (integer)
- **Response Body (`200 OK`):** `{"message": "User skill removed successfully"}`.
- **Possible Errors:** `404 Not Found`, `403 Forbidden`.

---

## 8. Course Skills (Curriculum Mapping) Endpoints

### 8.1 List Course-Skill Mappings
#### `GET /course-skills/`
- **Query Parameters:**
  - `course_id` (integer, optional)
  - `skill_id` (integer, optional)
- **Response Body (`200 OK`):** List of `CourseSkillResponse` objects.

---

### 8.2 Map Skill to Course
#### `POST /course-skills/`
Links a skill to a curriculum course.

- **Status Code:** `201 Created`
- **Request Body (`CourseSkillCreate`):**
  ```json
  {
    "course_id": 1,
    "skill_id": 5
  }
  ```
- **Response Body (`CourseSkillResponse`):**
  ```json
  {
    "id": 1,
    "course_id": 1,
    "skill_id": 5,
    "created_at": "2026-09-16T18:00:00Z"
  }
  ```
- **Possible Errors:**
  - `404 Not Found`: Course or Skill ID not found.
  - `400 Bad Request`: Skill is already mapped to this course.

---

### 8.3 Delete Course-Skill Mapping
#### `DELETE /course-skills/{id}`
Removes a skill mapping from a curriculum course.

- **Path Parameter:** `id` (integer)
- **Response Body (`200 OK`):** `{"message": "Skill mapping removed from course successfully"}`.
- **Possible Errors:** `404 Not Found`.
