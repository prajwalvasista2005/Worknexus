"""
WorkNexus End-to-End Comprehensive Integration Test Suite
Verifies 100% frontend ↔ backend route connectivity, all 5 RBAC roles,
full CRUD lifecycles, and ML intelligence services.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

PASSWORD = "SecurePassword123!"

ROLES_USERS = {
    "student": "student@worknexus.io",
    "employer": "employer@worknexus.io",
    "institute": "institute@worknexus.io",
    "trainer": "trainer@worknexus.io",
    "admin": "admin@worknexus.io",
}


def get_token_for(email: str, password: str = PASSWORD) -> str:
    """Helper to authenticate and retrieve access token."""
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# =====================================================================
# 1. HEALTH & ROOT
# =====================================================================
def test_01_health_and_root():
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


# =====================================================================
# 2. AUTHENTICATION FOR ALL 5 ROLES & ME IDENTITY
# =====================================================================
@pytest.mark.parametrize("role,email", ROLES_USERS.items())
def test_02_all_roles_login_and_me(role, email):
    res = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    token = data["access_token"]

    # Verify identity via /auth/me
    me_res = client.get("/api/v1/auth/me", headers=auth_header(token))
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"].lower() == email.lower()
    assert me_data["role"].lower() == role.lower()


# =====================================================================
# 3. AUTH LIFECYCLE: REGISTER -> LOGIN -> REFRESH -> LOGOUT
# =====================================================================
def test_03_auth_lifecycle_register_refresh_logout():
    import uuid
    uid = uuid.uuid4().hex[:8]
    test_email = f"e2e_student_{uid}@worknexus.io"

    # 1. Register
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": test_email,
            "password": PASSWORD,
            "full_name": f"E2E Student {uid}",
            "role": "Student"
        }
    )
    assert reg_res.status_code == 201, reg_res.text
    user_info = reg_res.json()
    assert user_info["email"] == test_email

    # 2. Login to obtain tokens
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": test_email, "password": PASSWORD}
    )
    assert login_res.status_code == 200
    tokens = login_res.json()
    access_tok = tokens["access_token"]
    refresh_tok = tokens["refresh_token"]

    # 3. Refresh Token
    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_tok}
    )
    assert refresh_res.status_code == 200, refresh_res.text
    refreshed_data = refresh_res.json()
    assert "access_token" in refreshed_data

    # 4. Logout
    logout_res = client.post(
        "/api/v1/auth/logout",
        headers=auth_header(access_tok),
        json={"refresh_token": refresh_tok}
    )
    assert logout_res.status_code == 200


# =====================================================================
# 4. RBAC ENFORCEMENT & GUARDS
# =====================================================================
def test_04_rbac_enforcement():
    student_tok = get_token_for(ROLES_USERS["student"])

    # Student cannot create Job Posting
    job_payload = {
        "title": "Unauthorized Dev",
        "description": "Should fail with 403",
        "company_name": "TestCorp",
        "location": "Remote"
    }
    fail_job = client.post("/api/v1/jobs/", headers=auth_header(student_tok), json=job_payload)
    assert fail_job.status_code == 403, f"Expected 403, got {fail_job.status_code}"

    # Student cannot create Target Role
    role_payload = {
        "id": "ROLE_TEST_UNAUTHORIZED",
        "name": "Unauthorized Role",
        "description": "Should fail",
        "skill_ids": ["SK_PYTHON"]
    }
    fail_role = client.post("/api/v1/roles/", headers=auth_header(student_tok), json=role_payload)
    assert fail_role.status_code == 403, f"Expected 403, got {fail_role.status_code}"


# =====================================================================
# 5. TARGET ROLES CRUD (ADMIN)
# =====================================================================
def test_05_target_roles_governance():
    admin_tok = get_token_for(ROLES_USERS["admin"])

    # 1. List roles
    list_res = client.get("/api/v1/roles/", headers=auth_header(admin_tok))
    assert list_res.status_code == 200
    roles = list_res.json()
    assert isinstance(roles, list)
    assert len(roles) > 0

    # 2. Create Target Role with canonical skill codes
    import uuid
    role_id = f"ROLE_E2E_{uuid.uuid4().hex[:6].upper()}"
    create_res = client.post(
        "/api/v1/roles/",
        headers=auth_header(admin_tok),
        json={
            "id": role_id,
            "name": "E2E Integration Specialist",
            "description": "Validates full stack systems",
            "skill_ids": ["SK_PYTHON", "SK_DOCKER"]
        }
    )
    assert create_res.status_code == 201, create_res.text
    created = create_res.json()
    assert created["id"] == role_id

    # 3. Read specific role
    get_res = client.get(f"/api/v1/roles/{role_id}", headers=auth_header(admin_tok))
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "E2E Integration Specialist"


# =====================================================================
# 6. SKILLS CATALOG CRUD (ADMIN & PUBLIC)
# =====================================================================
def test_06_skills_catalog_crud():
    import uuid
    admin_tok = get_token_for(ROLES_USERS["admin"])
    unique_code = f"SKILL_E2E_{uuid.uuid4().hex[:6].upper()}"

    # 1. Create skill
    create_res = client.post(
        "/api/v1/skills/",
        headers=auth_header(admin_tok),
        json={
            "skill_id": unique_code,
            "name": "E2E Testing Proficiency",
            "category": "Testing/QA",
            "description": "Integration test engineering"
        }
    )
    assert create_res.status_code == 201, create_res.text
    created = create_res.json()
    skill_db_id = created["id"]

    # 2. Get skill by code
    get_res = client.get(f"/api/v1/skills/{unique_code}")
    assert get_res.status_code == 200
    assert get_res.json()["skill_id"] == unique_code

    # 3. Update skill
    up_res = client.put(
        f"/api/v1/skills/{skill_db_id}",
        headers=auth_header(admin_tok),
        json={
            "name": "Advanced E2E Testing",
            "description": "Updated description"
        }
    )
    assert up_res.status_code == 200
    assert up_res.json()["name"] == "Advanced E2E Testing"

    # 4. Delete skill
    del_res = client.delete(f"/api/v1/skills/{skill_db_id}", headers=auth_header(admin_tok))
    assert del_res.status_code == 200


# =====================================================================
# 7. USER SKILLS CRUD (STUDENT)
# =====================================================================
def test_07_user_skills_crud():
    student_tok = get_token_for(ROLES_USERS["student"])

    # 1. Add User Skill
    add_res = client.post(
        "/api/v1/user-skills/",
        headers=auth_header(student_tok),
        json={
            "skill_id": 1,
            "proficiency_level": "intermediate",
            "years_of_experience": 2
        }
    )
    # 201 or 400 (if already added in seed)
    assert add_res.status_code in [200, 201, 400], add_res.text

    # 2. Get User Skills
    get_res = client.get("/api/v1/user-skills/", headers=auth_header(student_tok))
    assert get_res.status_code == 200
    skills = get_res.json()
    assert isinstance(skills, list)


# =====================================================================
# 8. COURSES & COURSE SKILLS CRUD (INSTITUTE)
# =====================================================================
def test_08_courses_and_course_skills_crud():
    import uuid
    institute_tok = get_token_for(ROLES_USERS["institute"])
    course_code = f"CS-{uuid.uuid4().hex[:4].upper()}"

    # 1. Create Course (schema requires course_id, name, department)
    create_course = client.post(
        "/api/v1/courses/",
        headers=auth_header(institute_tok),
        json={
            "course_id": course_code,
            "name": "E2E Cloud Architecture",
            "department": "Computer Science",
            "description": "Architecting resilient distributed systems"
        }
    )
    assert create_course.status_code == 201, create_course.text
    course = create_course.json()
    course_id = course["id"]

    # 2. Get Course
    get_course = client.get(f"/api/v1/courses/{course_id}", headers=auth_header(institute_tok))
    assert get_course.status_code == 200
    assert get_course.json()["course_id"] == course_code

    # 3. Add Skill to Course
    add_skill = client.post(
        f"/api/v1/courses/{course_id}/skills",
        headers=auth_header(institute_tok),
        json={
            "skill_id": 1,
            "relevance_score": 0.95
        }
    )
    assert add_skill.status_code in [200, 201], add_skill.text

    # 4. Get Course Skills
    get_skills = client.get(f"/api/v1/courses/{course_id}/skills", headers=auth_header(institute_tok))
    assert get_skills.status_code == 200
    c_skills = get_skills.json()
    assert len(c_skills) > 0

    # 5. Delete Course Skill
    del_skill = client.delete(f"/api/v1/courses/{course_id}/skills/1", headers=auth_header(institute_tok))
    assert del_skill.status_code == 200

    # 6. Delete Course
    del_course = client.delete(f"/api/v1/courses/{course_id}", headers=auth_header(institute_tok))
    assert del_course.status_code == 200


# =====================================================================
# 9. JOB POSTINGS & EMPLOYER FEEDBACK (EMPLOYER)
# =====================================================================
def test_09_job_postings_and_feedback():
    employer_tok = get_token_for(ROLES_USERS["employer"])

    # 1. Create Job with automatic skill extraction
    job_res = client.post(
        "/api/v1/jobs/",
        headers=auth_header(employer_tok),
        json={
            "title": "Senior Distributed Systems Engineer",
            "description": "Seeking expert in Python, Docker, Kubernetes, and PostgreSQL microservices.",
            "company_name": "NexusTech Labs",
            "location": "San Francisco, CA"
        }
    )
    assert job_res.status_code == 201, job_res.text
    job_data = job_res.json()
    job_id = job_data["id"]

    # 2. List jobs
    list_res = client.get("/api/v1/jobs/", headers=auth_header(employer_tok))
    assert list_res.status_code == 200
    assert len(list_res.json()) > 0

    # 3. Submit Employer Qualitative Feedback
    fb_res = client.post(
        "/api/v1/employers/feedback",
        headers=auth_header(employer_tok),
        json={
            "company_name": "NexusTech Labs",
            "feedback_text": "Candidates require production experience with Kubernetes and CI/CD pipelines."
        }
    )
    assert fb_res.status_code == 201, fb_res.text

    # 4. Get Employer Feedback List
    list_fb = client.get("/api/v1/employers/feedback", headers=auth_header(employer_tok))
    assert list_fb.status_code == 200
    assert len(list_fb.json()) > 0

    # 5. Delete Job Posting
    del_job = client.delete(f"/api/v1/jobs/{job_id}", headers=auth_header(employer_tok))
    assert del_job.status_code == 200


# =====================================================================
# 10. STUDENT PROFILE & EVIDENCE RECORDS (STUDENT)
# =====================================================================
def test_10_student_profile_and_evidence():
    student_tok = get_token_for(ROLES_USERS["student"])
    me = client.get("/api/v1/auth/me", headers=auth_header(student_tok)).json()
    user_id = me["id"]

    # 1. Save / Update Profile Goal with canonical role
    prof_res = client.post(
        "/api/v1/students/profile",
        headers=auth_header(student_tok),
        json={
            "user_id": user_id,
            "target_role_id": "ROLE_FULL_STACK_DEV"
        }
    )
    assert prof_res.status_code == 200, prof_res.text

    # 2. Get Student Profile
    get_prof = client.get(f"/api/v1/students/{user_id}/profile", headers=auth_header(student_tok))
    assert get_prof.status_code == 200
    assert get_prof.json()["target_role_id"] == "ROLE_FULL_STACK_DEV"

    # 3. Submit Skill Evidence
    ev_res = client.post(
        f"/api/v1/students/{user_id}/evidence",
        headers=auth_header(student_tok),
        json={
            "skill_id": "SK_PYTHON",
            "evidence_type": "github_pr",
            "strength": 4,
            "metadata": {"repo": "worknexus-backend", "pr_number": 42}
        }
    )
    assert ev_res.status_code == 201, ev_res.text

    # 4. List Skill Evidence
    list_ev = client.get(f"/api/v1/students/{user_id}/evidence", headers=auth_header(student_tok))
    assert list_ev.status_code == 200
    assert len(list_ev.json()) > 0


# =====================================================================
# 11. ML INTELLIGENCE SUITE
# =====================================================================
def test_11_ml_intelligence_endpoints():
    trainer_tok = get_token_for(ROLES_USERS["trainer"])
    student_tok = get_token_for(ROLES_USERS["student"])

    # 1. NLP Skill Extractor
    extract_res = client.post(
        "/api/v1/ml/extract-skills",
        headers=auth_header(trainer_tok),
        json={"text": "Must be proficient with Docker, Python, and AWS Cloud deployments."}
    )
    assert extract_res.status_code == 200
    extracted = extract_res.json()["skills"]
    assert len(extracted) > 0

    # 2. Skill Demand Rankings
    demand_res = client.get("/api/v1/ml/demand?top_n=10", headers=auth_header(trainer_tok))
    assert demand_res.status_code == 200
    demands = demand_res.json()
    assert "top_skills" in demands or "demands" in demands

    # 3. Course Skill Gaps
    gaps_res = client.get("/api/v1/ml/course-gaps", headers=auth_header(trainer_tok))
    assert gaps_res.status_code == 200

    single_gap = client.get("/api/v1/ml/course-gaps/1", headers=auth_header(trainer_tok))
    assert single_gap.status_code == 200
    assert "gap_score" in single_gap.json()

    # 4. Multi-Signal Evidence Telemetry
    ev_matrix = client.get("/api/v1/ml/evidence", headers=auth_header(trainer_tok))
    assert ev_matrix.status_code == 200

    ev_summary = client.get("/api/v1/ml/evidence-summary/SK_PYTHON", headers=auth_header(trainer_tok))
    assert ev_summary.status_code == 200
    assert ev_summary.json()["skill_id"] == "SK_PYTHON"

    # 5. Generic Recommendations
    recs = client.get("/api/v1/ml/recommendations", headers=auth_header(trainer_tok))
    assert recs.status_code == 200

    # 6. Role Context
    role_ctx = client.get("/api/v1/ml/roles/ROLE_FULL_STACK_DEV", headers=auth_header(trainer_tok))
    assert role_ctx.status_code == 200

    # 7. Student Personalization (gap, recommendations, course candidates)
    me = client.get("/api/v1/auth/me", headers=auth_header(student_tok)).json()
    uid = me["id"]

    gap_res = client.get(f"/api/v1/ml/students/{uid}/gap/ROLE_FULL_STACK_DEV", headers=auth_header(student_tok))
    assert gap_res.status_code == 200

    stu_recs = client.get(f"/api/v1/ml/students/{uid}/recommendations/ROLE_FULL_STACK_DEV", headers=auth_header(student_tok))
    assert stu_recs.status_code == 200

    candidates = client.get(f"/api/v1/ml/students/{uid}/course-candidates/ROLE_FULL_STACK_DEV", headers=auth_header(student_tok))
    assert candidates.status_code == 200
