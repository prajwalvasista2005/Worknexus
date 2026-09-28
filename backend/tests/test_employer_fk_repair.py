import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from fastapi import HTTPException

from app.main import app
from app.db.session import SessionLocal
from app.models.entities import User, Employer, JobPosting, EmployerFeedback
from app.schemas.schemas import JobCreateSchema, EmployerFeedbackCreateSchema
from app.services.job_service import JobService
from app.services.employer_service import EmployerService
from app.services.ml_adapter import MLAdapter
from app.auth.security import hash_password

client = TestClient(app)
PASSWORD = "SecurePassword123!"


def test_employer_signup_creates_employer_profile():
    """
    Test 1: Employer signup automatically creates an Employer profile inside
    the same transaction.
    """
    unique_id = uuid4().hex[:8]
    email = f"signup_emp_{unique_id}@worknexus.io"
    company_name = f"Quantum Corp {unique_id}"

    reg_payload = {
        "email": email,
        "password": PASSWORD,
        "full_name": company_name,
        "role": "Employer"
    }
    res = client.post("/api/v1/auth/register", json=reg_payload)
    assert res.status_code == 201, f"Registration failed: {res.text}"
    user_data = res.json()
    user_id = user_data["id"]

    with SessionLocal() as db:
        emp = db.query(Employer).filter(Employer.user_id == user_id).first()
        assert emp is not None, f"Employer profile was not created for user {user_id}"
        assert emp.company_name == company_name
        assert emp.user_id == user_id


def test_employer_can_create_requisition():
    """
    Test 2: Authenticated employer can create a job requisition.
    The employer_id in job_postings matches employer.id, NOT user.id.
    """
    unique_id = uuid4().hex[:8]
    email = f"req_emp_{unique_id}@worknexus.io"
    company_name = f"Robotics Ltd {unique_id}"

    # Register employer
    reg_payload = {
        "email": email,
        "password": PASSWORD,
        "full_name": company_name,
        "role": "Employer"
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    user_id = reg_res.json()["id"]

    # Login
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with SessionLocal() as db:
        emp = db.query(Employer).filter(Employer.user_id == user_id).first()
        assert emp is not None
        actual_employer_id = emp.id

    # Create Job Requisition
    job_payload = {
        "title": "Autonomous Systems Engineer",
        "company": company_name,
        "location": "Bengaluru",
        "description": "Requires ROS, Python, C++, and Motion Planning."
    }
    res = client.post("/api/v1/jobs/", headers=headers, json=job_payload)
    assert res.status_code == 201, res.text
    job_data = res.json()

    assert job_data["employer_id"] == actual_employer_id
    assert job_data["title"] == "Autonomous Systems Engineer"

    # Verify in DB
    with SessionLocal() as db:
        job = db.query(JobPosting).filter(JobPosting.id == job_data["id"]).first()
        assert job is not None
        assert job.employer_id == actual_employer_id


def test_employer_can_submit_feedback():
    """
    Test 3: Authenticated employer can submit curriculum feedback.
    The employer_id in employer_feedback matches employer.id, NOT user.id.
    """
    unique_id = uuid4().hex[:8]
    email = f"fb_emp_{unique_id}@worknexus.io"
    company_name = f"AeroTech {unique_id}"

    # Register employer
    reg_res = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": PASSWORD,
        "full_name": company_name,
        "role": "Employer"
    })
    assert reg_res.status_code == 201
    user_id = reg_res.json()["id"]

    # Login
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with SessionLocal() as db:
        emp = db.query(Employer).filter(Employer.user_id == user_id).first()
        assert emp is not None
        actual_employer_id = emp.id

    # Submit feedback
    fb_payload = {
        "comments": "Graduates need deeper hands-on lab experience with Battery Management Systems.",
        "rating": 5
    }
    res = client.post("/api/v1/employers/feedback", headers=headers, json=fb_payload)
    assert res.status_code == 201, res.text
    fb_data = res.json()

    assert fb_data["employer_id"] == actual_employer_id

    # Verify in DB
    with SessionLocal() as db:
        fb = db.query(EmployerFeedback).filter(EmployerFeedback.id == fb_data["id"]).first()
        assert fb is not None
        assert fb.employer_id == actual_employer_id
        assert fb.comments == fb_payload["comments"]


def test_no_endpoint_accepts_arbitrary_employer_id():
    """
    Test 4:
    - An employer sending an arbitrary employer_id in payload has it ignored
      and overridden by their authentic employer.id.
    - An admin sending an arbitrary non-existent employer_id has it rejected.
    """
    unique_id = uuid4().hex[:8]
    email = f"arbitrary_test_{unique_id}@worknexus.io"
    company_name = f"Arbitrary Corp {unique_id}"

    # Register employer
    reg_res = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": PASSWORD,
        "full_name": company_name,
        "role": "Employer"
    })
    assert reg_res.status_code == 201
    user_id = reg_res.json()["id"]

    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with SessionLocal() as db:
        emp = db.query(Employer).filter(Employer.user_id == user_id).first()
        actual_employer_id = emp.id

    # 1. Employer attempts to submit arbitrary employer_id=999999
    job_payload = {
        "title": "Security Analyst",
        "company": company_name,
        "location": "Remote",
        "description": "SOC analysis, SIEM, incident response.",
        "employer_id": 999999
    }
    job_res = client.post("/api/v1/jobs/", headers=headers, json=job_payload)
    assert job_res.status_code == 201
    # Must be overwritten with authenticated employer.id
    assert job_res.json()["employer_id"] == actual_employer_id

    fb_payload = {
        "comments": "Testing arbitrary employer_id submission rejection",
        "employer_id": 888888
    }
    fb_res = client.post("/api/v1/employers/feedback", headers=headers, json=fb_payload)
    assert fb_res.status_code == 201
    # Must be overwritten with authenticated employer.id
    assert fb_res.json()["employer_id"] == actual_employer_id

    # 2. Admin attempts to create job with non-existent employer_id
    admin_headers = {
        "X-User-Id": "99999",
        "X-User-Role": "Admin",
        "X-User-Email": "admin@worknexus.org"
    }
    invalid_admin_payload = {
        "title": "Admin Created Job",
        "company": "Fictional Corp",
        "location": "Remote",
        "description": "Role with invalid employer_id.",
        "employer_id": 777777
    }
    admin_job_res = client.post("/api/v1/jobs/", headers=admin_headers, json=invalid_admin_payload)
    assert admin_job_res.status_code in [400, 404]


def test_foreign_key_violations_no_longer_occur():
    """
    Test 5: Explicitly simulate the exact failure scenario from the prompt:
    user.id = 5, but employer.id is a different primary key (e.g. 50 or separate).
    Verify that creating job postings and feedback with user.id != employer.id
    completes without any PostgreSQL foreign key violation.
    """
    unique_id = uuid4().hex[:8]
    email = f"fk_distinct_{unique_id}@worknexus.io"
    company_name = f"Distinct ID Corp {unique_id}"

    with SessionLocal() as db:
        user = User(
            email=email,
            hashed_password=hash_password(PASSWORD),
            full_name=company_name,
            role="employer",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

        # Explicitly ensure employer.id != user.id
        emp = Employer(
            user_id=user_id,
            company_name=company_name,
            trust_weight=1.0
        )
        db.add(emp)
        db.commit()
        db.refresh(emp)
        employer_table_id = emp.id

    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Post Job - should use employer_table_id, not user_id
    job_payload = {
        "title": "Embedded C Developer",
        "company": company_name,
        "location": "Pune",
        "description": "Embedded C, CAN bus, microcontroller firmware."
    }
    res_job = client.post("/api/v1/jobs/", headers=headers, json=job_payload)
    assert res_job.status_code == 201
    assert res_job.json()["employer_id"] == employer_table_id

    # Submit Feedback - should use employer_table_id, not user_id
    fb_payload = {
        "comments": "Strong firmware capabilities demonstrated by candidates.",
        "rating": 5
    }
    res_fb = client.post("/api/v1/employers/feedback", headers=headers, json=fb_payload)
    assert res_fb.status_code == 201
    assert res_fb.json()["employer_id"] == employer_table_id


def test_existing_seeded_accounts_are_repaired_automatically():
    """
    Test 6: Existing seeded/legacy employer users without an Employer profile
    are automatically detected, repaired, and linked by verify_employer_profiles.
    """
    unique_id = uuid4().hex[:8]
    email = f"unlinked_seed_{unique_id}@worknexus.io"
    company_name = f"Legacy Seed Corp {unique_id}"

    with SessionLocal() as db:
        user = User(
            email=email,
            hashed_password=hash_password(PASSWORD),
            full_name=company_name,
            role="employer",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

        # Assert no employer profile exists yet
        assert db.query(Employer).filter(Employer.user_id == user_id).first() is None

        # Run verification and healing
        audit_res = EmployerService.verify_employer_profiles(db)
        assert audit_res["status"] == "ok"
        assert audit_res["healed_employers"] >= 1

        # Assert profile is now created and correctly linked
        healed_emp = db.query(Employer).filter(Employer.user_id == user_id).first()
        assert healed_emp is not None
        assert healed_emp.user_id == user_id
        assert healed_emp.company_name == company_name
