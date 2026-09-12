# WorkNexus API Reference Documentation

> **Base URL:** `http://127.0.0.1:8000`  
> **Interactive Documentation (Swagger UI):** `http://127.0.0.1:8000/docs`  
> **Alternative Documentation (ReDoc):** `http://127.0.0.1:8000/redoc`  
> **Current Version:** `1.0.0`

---

## 1. Global Headers & Conventions

All endpoints follow standard RESTful HTTP semantics.

### Standard Request Headers
| Header | Required For | Format / Value | Description |
| :--- | :--- | :--- | :--- |
| `Content-Type` | `POST`, `PUT`, `PATCH` | `application/json` | Specifies JSON body payload. |
| `Accept` | All Requests | `application/json` | Informs server of accepted response format. |
| `Authorization` | Protected Routes | `Bearer <access_token>` | OAuth2 Bearer token obtained from `/auth/login`. |

### Standard Response Structure
- Successful requests return JSON representations corresponding to defined Pydantic schemas.
- Error responses return a JSON object containing a `detail` message:
  ```json
  {
    "detail": "Error description message"
  }
  ```

---

## 2. JWT Authentication Usage

WorkNexus secures private endpoints using signed JSON Web Tokens (JWT) adhering to RFC 7519.

### Token Specifications
- **Algorithm:** `HS256` (HMAC-SHA256)
- **Token Type:** `bearer`
- **Default Lifetime:** 30 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)

### Token Claims
Decoded payload structure:
```json
{
  "sub": "user@example.com",
  "iat": 1773449400,
  "exp": 1773451200
}
```
- `sub` (Subject): The authenticated user's unique email address.
- `iat` (Issued At): UNIX timestamp indicating when the token was signed.
- `exp` (Expiration): UNIX timestamp after which the token is invalid.

### How to Authenticate Requests
Include the token in the HTTP `Authorization` header prefixed with `Bearer `:
```http
GET /auth/me HTTP/1.1
Host: 127.0.0.1:8000
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 3. Interactive Swagger Authorization Steps

FastAPI provides built-in Swagger UI with integrated OAuth2 authorization.

```text
Step 1: Open Browser          Step 2: Login via API           Step 3: Authorize Swagger       Step 4: Execute Protected
┌───────────────────────┐    ┌────────────────────────┐      ┌─────────────────────────┐     ┌────────────────────────┐
│ Visit /docs in browser│───►│ Execute POST /auth/login│────► │ Click "Authorize" button│───► │ Now test GET /auth/me  │
│                       │    │ Copy access_token string│      │ Paste token into Value  │     │ Requests send Bearer!  │
└───────────────────────┘    └────────────────────────┘      └─────────────────────────┘     └────────────────────────┘
```

1. Navigate to **`http://127.0.0.1:8000/docs`** in your browser.
2. Scroll to **`POST /auth/login`**, click **Try it out**, fill in registered credentials, and click **Execute**.
3. From the `200 OK` response body, copy the value of `access_token` (do not include quotes).
4. Scroll to the top right of the Swagger page and click the green **Authorize** (lock icon) button.
5. In the **Value** field, enter your token (or `Bearer <your_token>`), then click **Authorize** and **Close**.
6. All protected endpoints (such as `GET /auth/me`) will now automatically include the bearer token in every request.

---

## 4. Current Endpoints (Implemented)

### System Health Check
#### `GET /`
Returns the operational health status of the backend service.

- **Authentication Required:** No
- **Request Schema:** None
- **Response Schema:** Object
- **Example Request:**
  ```bash
  curl -X GET "http://127.0.0.1:8000/"
  ```
- **Example Response (`200 OK`):**
  ```json
  {
    "message": "SkillSync is up and running!"
  }
  ```

---

### Authentication Endpoints

---

#### 1. Register User
#### `POST /auth/register`
Creates a new user profile in the database, securely hashes the password using bcrypt, and returns the profile details.

- **Authentication Required:** No
- **Status Code on Success:** `201 Created`

##### Request Schema (`UserCreate`)
| Field | Type | Required | Constraints | Description |
| :--- | :--- | :--- | :--- | :--- |
| `email` | `string` | Yes | Valid email format | User's unique email address. |
| `password` | `string` | Yes | Non-empty string | Plaintext password (hashed before storage). |
| `full_name` | `string` | Yes | Max 255 chars | Full legal or display name. |
| `role` | `string` | Yes | Max 50 chars | User role (`student`, `employer`, `instructor`, `admin`). |

##### Response Schema (`UserResponse`)
| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | `integer` | Primary key database identifier. |
| `email` | `string` | Registered email address. |
| `full_name` | `string` | User's full name. |
| `role` | `string` | Assigned system role. |
| `is_active` | `boolean` | Account active flag (default: `true`). |
| `created_at` | `string` (ISO 8601) | Timestamp of registration. |

##### Example Request
```bash
curl -X POST "http://127.0.0.1:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "developer@example.com",
    "password": "SecurePassword123!",
    "full_name": "Prajwal Vasista",
    "role": "student"
  }'
```

##### Example Response (`201 Created`)
```json
{
  "id": 1,
  "email": "developer@example.com",
  "full_name": "Prajwal Vasista",
  "role": "student",
  "is_active": true,
  "created_at": "2026-09-13T01:10:00.000000Z"
}
```

##### Possible Errors
| HTTP Status | Reason | Response Body |
| :--- | :--- | :--- |
| `400 Bad Request` | Email already exists | `{"detail": "Email already registered"}` |
| `422 Unprocessable Entity` | Malformed JSON or invalid email | `{"detail": [{"loc": ["body", "email"], "msg": "value is not a valid email address", "type": "value_error"}]}` |

---

#### 2. User Login
#### `POST /auth/login`
Authenticates user credentials against the stored bcrypt hash and returns a signed JWT access token.

- **Authentication Required:** No
- **Status Code on Success:** `200 OK`

##### Request Schema (`UserLogin`)
| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `email` | `string` | Yes | Registered account email. |
| `password` | `string` | Yes | Account password. |

##### Response Schema (`Token`)
| Field | Type | Description |
| :--- | :--- | :--- |
| `access_token` | `string` | Signed JWT token string. |
| `token_type` | `string` | Standard token type (`"bearer"`). |

##### Example Request
```bash
curl -X POST "http://127.0.0.1:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "developer@example.com",
    "password": "SecurePassword123!"
  }'
```

##### Example Response (`200 OK`)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZXZlbG9wZXJAZXhhbXBsZS5jb20iLCJleHAiOjE3NzM0NTEyMDAsImlhdCI6MTc3MzQ0OTQwMH0.abcdef...",
  "token_type": "bearer"
}
```

##### Possible Errors
| HTTP Status | Reason | Response Body | Headers |
| :--- | :--- | :--- | :--- |
| `401 Unauthorized` | Invalid email or incorrect password | `{"detail": "Incorrect email or password"}` | `WWW-Authenticate: Bearer` |
| `400 Bad Request` | User account is deactivated | `{"detail": "Inactive user account"}` | None |
| `422 Unprocessable Entity` | Missing required fields | `{"detail": [{"loc": ["body", "email"], "msg": "field required"}]}` | None |

---

#### 3. Current Authenticated User Profile
#### `GET /auth/me`
Fetches the profile details of the currently authenticated user identified by the Bearer token.

- **Authentication Required:** **Yes** (`Bearer <token>`)
- **Status Code on Success:** `200 OK`

##### Request Schema
None (parameters extracted from the `Authorization: Bearer <token>` header).

##### Response Schema (`UserResponse`)
Same as `POST /auth/register` response (`id`, `email`, `full_name`, `role`, `is_active`, `created_at`).

##### Example Request
```bash
curl -X GET "http://127.0.0.1:8000/auth/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

##### Example Response (`200 OK`)
```json
{
  "id": 1,
  "email": "developer@example.com",
  "full_name": "Prajwal Vasista",
  "role": "student",
  "is_active": true,
  "created_at": "2026-09-13T01:10:00.000000Z"
}
```

##### Possible Errors
| HTTP Status | Reason | Response Body | Headers |
| :--- | :--- | :--- | :--- |
| `401 Unauthorized` | Missing `Authorization` header | `{"detail": "Not authenticated"}` | None |
| `401 Unauthorized` | Expired, forged, or invalid token | `{"detail": "Could not validate credentials"}` | `WWW-Authenticate: Bearer` |
| `400 Bad Request` | User has been deactivated | `{"detail": "Inactive user"}` | None |

---

## 5. Future Planned APIs (NOT YET IMPLEMENTED)

> **Note for Collaborators & ML Engineers:**  
> The endpoints below are part of the WorkNexus development roadmap. They are **NOT YET IMPLEMENTED** in the current codebase.

### 1. Skills & Assessments `[PLANNED]`
- **`GET /skills`**  
  *Description:* List all available standard skills in the global taxonomy (with optional category filter).  
  *Auth:* Public / Optional Bearer
- **`GET /users/me/skills`**  
  *Description:* Retrieve the authenticated user's declared and verified skills with proficiency levels.  
  *Auth:* Required Bearer
- **`POST /users/me/skills`**  
  *Description:* Add a skill to the user's profile or submit assessment results for verification.  
  *Auth:* Required Bearer (`student`, `jobseeker`)
- **`POST /skills/assess`**  
  *Description:* Submit assessment quiz answers to verify a skill proficiency level.  
  *Auth:* Required Bearer

### 2. Courses & Learning Paths `[PLANNED]`
- **`GET /courses`**  
  *Description:* Search and filter courses by skill, difficulty, or provider.  
  *Auth:* Public
- **`GET /courses/{course_id}`**  
  *Description:* Get complete curriculum, requirements, and target skills for a specific course.  
  *Auth:* Public
- **`POST /courses`**  
  *Description:* Create a course listing.  
  *Auth:* Required Bearer (`instructor`, `institute`, `admin`)

### 3. Jobs & Opportunities `[PLANNED]`
- **`GET /jobs`**  
  *Description:* List active job postings with pagination and skill-tag filtering.  
  *Auth:* Public
- **`POST /jobs`**  
  *Description:* Publish a new job opening with required skill weights.  
  *Auth:* Required Bearer (`employer`, `admin`)
- **`GET /jobs/{job_id}`**  
  *Description:* Get detailed job requirements and employer profile.  
  *Auth:* Public
- **`POST /jobs/{job_id}/apply`**  
  *Description:* Apply to a job posting using the candidate's verified skill profile.  
  *Auth:* Required Bearer (`student`, `jobseeker`)

### 4. Machine Learning & Recommendations `[PLANNED]`
- **`GET /recommendations/jobs`**  
  *Description:* Returns a personalized, ranked list of jobs calculated by matching the user's skill vector against job requirements.  
  *Auth:* Required Bearer
- **`GET /recommendations/courses`**  
  *Description:* Recommends learning paths and courses designed to close detected skill gaps for target job profiles.  
  *Auth:* Required Bearer
- **`POST /ml/match-score`**  
  *Description:* Computes an on-demand compatibility match percentage between a candidate profile and a specific job posting.  
  *Auth:* Required Bearer
- **`POST /ml/extract-skills`**  
  *Description:* Natural language processing (NLP) endpoint to extract verified skills from raw resume or job description text.  
  *Auth:* Required Bearer
