import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.db.session import SessionLocal
from app.models.entities import User, Employer, JobPosting
from app.schemas.schemas import JobCreateSchema
from app.services.job_service import JobService
from app.services.ml_adapter import MLAdapter
from fastapi import HTTPException

client = TestClient(app)

PASSWORD = "SecurePassword123!"


def test_employer_without_profile_fails_validation():
    """
    Validation Test:
    When an authenticated employer has no Employer profile row in the employers table,
    creating a job posting must return HTTP 404 (or 400) with a clear message.
    Crucially, a database IntegrityError must NOT reach the client.
    """
    unique_id = uuid4().hex[:8]
    email = f"employer_no_profile_{unique_id}@worknexus.io"

    # 1. Create a user with Employer role but NO Employer row
    with SessionLocal() as db:
        from app.auth.security import hash_password
        user = User(
            email=email,
            hashed_password=hash_password(PASSWORD),
            full_name=f"Profileless Employer {unique_id}",
            role="employer",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

        # Verify no Employer row exists for this user
        existing_emp = db.query(Employer).filter(Employer.user_id == user_id).first()
        assert existing_emp is None

    # 2. Login as the newly created employer account
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login_res.status_code == 200, login_res.text
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Attempt to create a job posting
    job_payload = {
        "title": "Cloud Architect",
        "company": "Missing Profile Corp",
        "location": "Remote",
        "description": "Looking for Python and Kubernetes cloud architect."
    }
    res = client.post("/api/v1/jobs/", headers=headers, json=job_payload)

    # 4. Must return 404 (or 400) with a clear message, NOT 500 or unhandled DB IntegrityError
    assert res.status_code in [400, 404], f"Expected 400 or 404, got {res.status_code}: {res.text}"
    detail = res.json().get("detail", "")
    assert "Employer profile not found" in detail, f"Expected clear message, got: {detail}"


def test_employer_job_creation_lifecycle_integration():
    """
    Lifecycle Integration Test (Task 7):
    - login employer account
    - create job posting
    - verify row inserted successfully
    - verify employer_id references a valid employers table record
    """
    unique_id = uuid4().hex[:8]
    email = f"valid_employer_{unique_id}@worknexus.io"
    company_name = f"Valid Corp {unique_id}"

    # 1. Provision employer user and matching Employer profile row
    with SessionLocal() as db:
        from app.auth.security import hash_password
        user = User(
            email=email,
            hashed_password=hash_password(PASSWORD),
            full_name=f"Valid Employer {unique_id}",
            role="employer",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

        # Create distinct Employer row with auto-increment ID
        employer = Employer(
            user_id=user_id,
            company_name=company_name,
            trust_weight=1.0
        )
        db.add(employer)
        db.commit()
        db.refresh(employer)
        employer_id = employer.id

    # 2. Login employer account
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Create job posting
    job_payload = {
        "title": "Senior Backend Software Engineer",
        "company": company_name,
        "location": "Bengaluru",
        "description": "Requires strong expertise in Python, FastAPI, Docker, and PostgreSQL databases."
    }
    create_res = client.post("/api/v1/jobs/", headers=headers, json=job_payload)
    assert create_res.status_code == 201, f"Create job failed: {create_res.text}"
    job_data = create_res.json()

    created_job_id = job_data["id"]
    assigned_employer_id = job_data["employer_id"]

    # 4. Verify employer_id matches the employers table record (NOT the users table ID)
    assert assigned_employer_id == employer_id, f"Expected employer_id={employer_id}, got {assigned_employer_id}"

    # 5. Direct DB verification: verify row inserted successfully
    with SessionLocal() as db:
        stmt = select(JobPosting).where(JobPosting.id == created_job_id)
        db_job = db.execute(stmt).scalar_one_or_none()

        assert db_job is not None, f"JobPosting {created_job_id} not found in database"
        assert db_job.title == "Senior Backend Software Engineer"
        assert db_job.company_name == company_name

        # 6. Verify employer_id references a valid employers table record
        emp_stmt = select(Employer).where(Employer.id == db_job.employer_id)
        linked_employer = db.execute(emp_stmt).scalar_one_or_none()

        assert linked_employer is not None, f"Employer {db_job.employer_id} not found in employers table!"
        assert linked_employer.id == employer_id
        assert linked_employer.user_id == user_id
        assert linked_employer.company_name == company_name


def test_create_job_service_direct_rejects_invalid_employer_id():
    """
    Direct Service Validation Test:
    JobService.create_job() must reject an invalid employer_id that does not exist
    in the employers table, and not allow IntegrityError to escape.
    """
    adapter = MLAdapter()
    invalid_employer_id = 99999999

    with SessionLocal() as db:
        job_in = JobCreateSchema(
            title="Direct Test Role",
            company="Direct Test Corp",
            location="Remote",
            description="Testing invalid employer_id direct rejection.",
            employer_id=invalid_employer_id
        )

        with pytest.raises(HTTPException) as exc_info:
            JobService.create_job(db=db, job_in=job_in, ml_adapter=adapter)

        assert exc_info.value.status_code in [400, 404]
        assert "does not exist in employers table" in exc_info.value.detail or "Employer" in exc_info.value.detail
