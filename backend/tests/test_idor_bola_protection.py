import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.entities import User, Employer, JobPosting, Skill
from app.models.user_skills import UserSkill
from app.models.student_roles import TargetRole, StudentProfile
from app.auth.security import hash_password

client = TestClient(app)
PASSWORD = "SecurePassword123!"


@pytest.fixture
def auth_users():
    """Seeds two distinct employers and two distinct students for cross-user IDOR testing."""
    with SessionLocal() as db:
        # 1. Ensure TargetRole exists
        role = db.query(TargetRole).filter(TargetRole.id == "ROLE_FULL_STACK_DEV").first()
        if not role:
            role = TargetRole(
                id="ROLE_FULL_STACK_DEV",
                name="Full Stack Developer",
                description="Web development",
                is_active=True
            )
            db.add(role)
            db.commit()

        # 2. Employer 1
        emp1_user = db.query(User).filter(User.email == "emp1_idor@worknexus.io").first()
        if not emp1_user:
            emp1_user = User(
                email="emp1_idor@worknexus.io",
                hashed_password=hash_password(PASSWORD),
                full_name="Employer One Corp",
                role="employer",
                is_active=True
            )
            db.add(emp1_user)
            db.commit()
            db.refresh(emp1_user)

        emp1_prof = db.query(Employer).filter(Employer.user_id == emp1_user.id).first()
        if not emp1_prof:
            emp1_prof = Employer(company_name="Employer One Corp", user_id=emp1_user.id, trust_weight=1.0)
            db.add(emp1_prof)
            db.commit()
            db.refresh(emp1_prof)

        emp1_user_id = emp1_user.id
        emp1_prof_id = emp1_prof.id

        # 3. Employer 2
        emp2_user = db.query(User).filter(User.email == "emp2_idor@worknexus.io").first()
        if not emp2_user:
            emp2_user = User(
                email="emp2_idor@worknexus.io",
                hashed_password=hash_password(PASSWORD),
                full_name="Employer Two Corp",
                role="employer",
                is_active=True
            )
            db.add(emp2_user)
            db.commit()
            db.refresh(emp2_user)

        emp2_prof = db.query(Employer).filter(Employer.user_id == emp2_user.id).first()
        if not emp2_prof:
            emp2_prof = Employer(company_name="Employer Two Corp", user_id=emp2_user.id, trust_weight=1.0)
            db.add(emp2_prof)
            db.commit()
            db.refresh(emp2_prof)

        emp2_user_id = emp2_user.id
        emp2_prof_id = emp2_prof.id

        # 4. Student 1
        stu1_user = db.query(User).filter(User.email == "stu1_idor@worknexus.io").first()
        if not stu1_user:
            stu1_user = User(
                email="stu1_idor@worknexus.io",
                hashed_password=hash_password(PASSWORD),
                full_name="Student One",
                role="student",
                is_active=True
            )
            db.add(stu1_user)
            db.commit()
            db.refresh(stu1_user)

        stu1_prof = db.query(StudentProfile).filter(StudentProfile.user_id == stu1_user.id).first()
        if not stu1_prof:
            stu1_prof = StudentProfile(user_id=stu1_user.id, target_role_id="ROLE_FULL_STACK_DEV")
            db.add(stu1_prof)
            db.commit()

        stu1_user_id = stu1_user.id

        # 5. Student 2
        stu2_user = db.query(User).filter(User.email == "stu2_idor@worknexus.io").first()
        if not stu2_user:
            stu2_user = User(
                email="stu2_idor@worknexus.io",
                hashed_password=hash_password(PASSWORD),
                full_name="Student Two",
                role="student",
                is_active=True
            )
            db.add(stu2_user)
            db.commit()
            db.refresh(stu2_user)

        stu2_prof = db.query(StudentProfile).filter(StudentProfile.user_id == stu2_user.id).first()
        if not stu2_prof:
            stu2_prof = StudentProfile(user_id=stu2_user.id, target_role_id="ROLE_FULL_STACK_DEV")
            db.add(stu2_prof)
            db.commit()

        stu2_user_id = stu2_user.id

    # Login to get tokens
    def _login(email):
        res = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
        return res.json()["access_token"]

    return {
        "emp1_token": _login("emp1_idor@worknexus.io"),
        "emp1_id": emp1_prof_id,
        "emp1_user_id": emp1_user_id,
        "emp2_token": _login("emp2_idor@worknexus.io"),
        "emp2_id": emp2_prof_id,
        "emp2_user_id": emp2_user_id,
        "stu1_token": _login("stu1_idor@worknexus.io"),
        "stu1_user_id": stu1_user_id,
        "stu2_token": _login("stu2_idor@worknexus.io"),
        "stu2_user_id": stu2_user_id,
    }


def test_employer_cannot_delete_other_employer_job(auth_users):
    """BOLA check: Employer 2 cannot delete a job posting owned by Employer 1."""
    emp1_headers = {"Authorization": f"Bearer {auth_users['emp1_token']}"}
    emp2_headers = {"Authorization": f"Bearer {auth_users['emp2_token']}"}

    # 1. Employer 1 creates a job posting
    job_payload = {
        "title": "Confidential Project Lead",
        "company": "Employer One Corp",
        "location": "Bengaluru",
        "description": "Python, SQL, and distributed architecture."
    }
    create_res = client.post("/api/v1/jobs/", json=job_payload, headers=emp1_headers)
    assert create_res.status_code == 201
    job_id = create_res.json()["id"]

    # 2. Employer 2 attempts to delete Employer 1's job -> 403 Forbidden
    del_res = client.delete(f"/api/v1/jobs/{job_id}", headers=emp2_headers)
    assert del_res.status_code == 403
    assert "not have permission" in del_res.json()["detail"].lower() or "not authorized" in del_res.json()["detail"].lower()

    # 3. Employer 1 can delete their own job -> 200 OK
    own_del_res = client.delete(f"/api/v1/jobs/{job_id}", headers=emp1_headers)
    assert own_del_res.status_code == 200


def test_student_cannot_modify_other_student_profile(auth_users):
    """BOLA check: Student 2 cannot modify Student 1's profile."""
    stu1_headers = {"Authorization": f"Bearer {auth_users['stu1_token']}"}
    stu2_headers = {"Authorization": f"Bearer {auth_users['stu2_token']}"}

    # Student 2 tries to update Student 1's profile
    payload = {
        "user_id": auth_users["stu1_user_id"],
        "target_role_id": "ROLE_EV_TECHNICIAN"
    }
    tamper_res = client.post("/api/v1/students/profile", json=payload, headers=stu2_headers)
    assert tamper_res.status_code == 403

    # Student 1 updates their own profile -> 200 OK
    own_res = client.post("/api/v1/students/profile", json=payload, headers=stu1_headers)
    assert own_res.status_code == 200


def test_student_cannot_add_evidence_to_other_student(auth_users):
    """BOLA check: Student 2 cannot add skill evidence to Student 1's profile."""
    stu2_headers = {"Authorization": f"Bearer {auth_users['stu2_token']}"}
    stu1_headers = {"Authorization": f"Bearer {auth_users['stu1_token']}"}
    stu1_id = auth_users["stu1_user_id"]

    evidence_payload = {
        "skill_id": "SK_PYTHON",
        "evidence_type": "project",
        "strength": "advanced",
        "metadata": {"repo": "https://github.com/tamper/repo"}
    }
    # Tamper attempt -> 403 Forbidden
    tamper_res = client.post(f"/api/v1/students/{stu1_id}/evidence", json=evidence_payload, headers=stu2_headers)
    assert tamper_res.status_code == 403

    # Legitimate attempt by Student 1 -> 201 Created
    legit_res = client.post(f"/api/v1/students/{stu1_id}/evidence", json=evidence_payload, headers=stu1_headers)
    assert legit_res.status_code in (200, 201)
