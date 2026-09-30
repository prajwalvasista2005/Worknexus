import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.db.session import SessionLocal
from app.models.entities import User, Employer, JobPosting, JobSkill, Skill
from app.schemas.schemas import JobCreateSchema
from app.services.job_service import JobService
from app.services.employer_service import EmployerService
from app.services.ml_adapter import MLAdapter
from app.db.seed import verify_and_heal_profiles
from fastapi import HTTPException

client = TestClient(app)

PASSWORD = "SecurePassword123!"


def test_employer_registration_auto_provisions_profile():
    """
    Registration Flow Test (Task 7):
    Registering a new user with role 'Employer' must automatically provision
    a corresponding Employer profile row in the employers table.
    """
    unique_id = uuid4().hex[:8]
    email = f"registered_employer_{unique_id}@worknexus.io"
    company_name = f"Enterprise Corp {unique_id}"

    # 1. Register new employer via public API endpoint
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

    # 2. Verify an Employer profile row was automatically provisioned in DB
    with SessionLocal() as db:
        emp = db.query(Employer).filter(Employer.user_id == user_id).first()
        assert emp is not None, f"Employer profile was not auto-provisioned for user {user_id}"
        assert emp.company_name == company_name
        assert emp.user_id == user_id


def test_legacy_employer_account_healing():
    """
    Legacy Account Healing Test (Task 7):
    Users with role 'employer' that exist in users table but lack an Employer profile
    must be automatically healed by verify_and_heal_profiles.
    """
    unique_id = uuid4().hex[:8]
    email = f"legacy_employer_{unique_id}@worknexus.io"
    company_name = f"Legacy Corp {unique_id}"

    with SessionLocal() as db:
        from app.auth.security import hash_password
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

        # Explicitly verify no profile exists yet
        assert db.query(Employer).filter(Employer.user_id == user_id).first() is None

        # Run healing procedure
        heal_res = verify_and_heal_profiles(db)
        assert heal_res["healed_employers"] >= 1

        # Verify profile is now healed
        healed_emp = db.query(Employer).filter(Employer.user_id == user_id).first()
        assert healed_emp is not None
        assert healed_emp.company_name == company_name
        assert healed_emp.user_id == user_id


def test_missing_employer_profile_recovery_during_job_creation():
    """
    Missing Employer Profile Recovery Test (Task 4 & 5):
    When an authenticated employer user has NO pre-existing Employer row in the employers table,
    creating a job posting must NOT crash with ForeignKeyViolation or return 500.
    The system must defensively auto-provision the profile and successfully create the job posting.
    """
    unique_id = uuid4().hex[:8]
    email = f"unprofiled_employer_{unique_id}@worknexus.io"
    company_name = f"Self Healing Corp {unique_id}"

    # 1. Insert user directly with employer role but NO Employer record
    with SessionLocal() as db:
        from app.auth.security import hash_password
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

        assert db.query(Employer).filter(Employer.user_id == user_id).first() is None

    # 2. Login as the unprofiled employer
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login_res.status_code == 200, login_res.text
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Post a job demand requisition
    job_payload = {
        "title": "Principal Distributed Systems Engineer",
        "company": company_name,
        "location": "Remote",
        "description": "Requires advanced Go, Distributed Systems, gRPC, and Kubernetes."
    }
    res = client.post("/api/v1/jobs/", headers=headers, json=job_payload)
    assert res.status_code == 201, f"Expected 201 Created on missing profile recovery, got {res.status_code}: {res.text}"

    data = res.json()
    assert data["title"] == "Principal Distributed Systems Engineer"
    assert data["company"] == company_name
    assert data["employer_id"] is not None

    # 4. Verify DB state: Employer profile was created and JobPosting foreign key references it
    with SessionLocal() as db:
        emp = db.query(Employer).filter(Employer.user_id == user_id).first()
        assert emp is not None, "Employer profile was not automatically created!"
        assert emp.id == data["employer_id"]

        job = db.query(JobPosting).filter(JobPosting.id == data["id"]).first()
        assert job is not None
        assert job.employer_id == emp.id


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
    in the employers table and cannot be resolved to any user, without allowing
    an unhandled raw IntegrityError to escape.
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


def test_job_submission_resolves_string_skill_codes_to_integer_foreign_keys():
    """
    Verify that when job demand data is submitted from employer workspace:
    1. String skill codes (e.g. 'SK_PYTHON') or names (e.g. 'python') are queried or upserted into skills table.
    2. Resolved integer primary keys (id) are stored in job_skills.skill_id foreign key column.
    3. No InvalidTextRepresentation errors occur and foreign key integrity is preserved.
    """
    unique_id = uuid4().hex[:8]
    email = f"skill_employer_{unique_id}@worknexus.io"
    company_name = f"Skill Testing Corp {unique_id}"

    # 1. Provision employer user and Employer profile row
    with SessionLocal() as db:
        from app.auth.security import hash_password
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

        employer = Employer(
            user_id=user.id,
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

    # 3. Submit job requisition with string skill codes, names, and custom skills
    custom_skill_name = f"Quantum Computing {unique_id}"
    job_payload = {
        "title": "Quantum AI Lead",
        "company": company_name,
        "location": "Bengaluru",
        "description": "Looking for specialist with skills in Python, Docker, and Kubernetes microservices.",
        "required_skills": ["SK_PYTHON", "python", custom_skill_name]
    }
    create_res = client.post("/api/v1/jobs/", headers=headers, json=job_payload)
    assert create_res.status_code == 201, f"Job submission failed: {create_res.text}"
    job_data = create_res.json()
    created_job_id = job_data["id"]

    # 4. Verify in DB that job_skills records have integer skill_id foreign keys referencing skills(id)
    with SessionLocal() as db:
        job_skills_stmt = select(JobSkill).where(JobSkill.job_id == created_job_id)
        job_skills = list(db.execute(job_skills_stmt).scalars().all())

        assert len(job_skills) > 0, "Expected job_skills rows to be inserted"

        for js in job_skills:
            # Must strictly be an integer primary key, never a string code
            assert isinstance(js.skill_id, int), f"job_skills.skill_id was not an integer: {js.skill_id} ({type(js.skill_id)})"

            # Must exist in the skills table by primary key
            skill_stmt = select(Skill).where(Skill.id == js.skill_id)
            linked_skill = db.execute(skill_stmt).scalar_one_or_none()
            assert linked_skill is not None, f"Referenced skill id {js.skill_id} not found in skills table"
            assert isinstance(linked_skill.id, int)
            assert linked_skill.skill_id is not None
            assert len(linked_skill.skill_id) > 0

        # Verify the custom skill was upserted into skills table
        custom_skill_stmt = select(Skill).where(Skill.name == custom_skill_name)
        custom_skill = db.execute(custom_skill_stmt).scalar_one_or_none()
        assert custom_skill is not None, f"Custom skill '{custom_skill_name}' was not upserted into skills table"
        assert isinstance(custom_skill.id, int)
        assert any(js.skill_id == custom_skill.id for js in job_skills)
