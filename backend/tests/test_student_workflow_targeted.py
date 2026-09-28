import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.users import User
from app.models.skills import Skill
from app.models.student_roles import TargetRole, StudentProfile
from app.auth.jwt import create_access_token


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture
def student_auth():
    from app.auth.security import hash_password
    db = SessionLocal()
    try:
        # Ensure ROLE_EV_TECHNICIAN exists (needed by gap/course-candidates tests)
        role = db.query(TargetRole).filter(TargetRole.id == "ROLE_EV_TECHNICIAN").first()
        if not role:
            role = TargetRole(
                id="ROLE_EV_TECHNICIAN",
                name="EV Technician",
                description="Benchmark Role: EV battery diagnostics and powertrain electronics.",
                is_active=True,
            )
            db.add(role)
            db.commit()

        # Get or create a student user with a valid bcrypt hash
        user = db.query(User).filter(User.email == "test_student_workflow@worknexus.org").first()
        if not user:
            user = User(
                email="test_student_workflow@worknexus.org",
                hashed_password=hash_password("Password123!"),
                full_name="Targeted Test Student",
                role="student",
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # Ensure student has a StudentProfile pointing at ROLE_EV_TECHNICIAN
        from app.models.student_roles import StudentProfile
        profile = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
        if not profile:
            profile = StudentProfile(user_id=user.id, target_role_id="ROLE_EV_TECHNICIAN")
            db.add(profile)
            db.commit()

        token = create_access_token(data={"sub": user.email, "user_id": user.id, "role": "Student"})
        headers = {
            "Authorization": f"Bearer {token}",
            "X-User-Id": str(user.id),
            "X-User-Role": "Student",
            "X-User-Email": user.email,
        }
        return {"user_id": user.id, "headers": headers}
    finally:
        db.close()


def test_01_view_gaps(client, student_auth):
    """Workflow Step 1: View Gaps"""
    user_id = student_auth["user_id"]
    headers = student_auth["headers"]
    role_id = "ROLE_EV_TECHNICIAN"

    response = client.get(f"/api/v1/ml/students/{user_id}/gap/{role_id}?mode=live", headers=headers)
    assert response.status_code == 200, f"Gap endpoint failed: {response.text}"
    data = response.json()

    assert "missing_skills" in data or "skills_missing" in data
    missing = data.get("missing_skills") or data.get("skills_missing") or []
    print(f"\n[PASS] Step 1 View Gaps: Found {len(missing)} missing skills for {role_id}")
    assert len(missing) > 0, "Expected missing skills for target role"


def test_02_submit_evidence_by_skill_name_and_canonical_id(client, student_auth):
    """Workflow Step 2: Submit Evidence (both canonical skill_id and skill name)"""
    user_id = student_auth["user_id"]
    headers = student_auth["headers"]

    # Submission A: with canonical skill_id
    payload_canonical = {
        "skill_id": "SK_CAN",
        "evidence_type": "project",
        "strength": "advanced",
        "metadata": {
            "repo": "https://github.com/worknexus/can-bus-driver",
            "notes": "Implemented automotive CAN bus transceiver"
        }
    }
    res_a = client.post(f"/api/v1/students/{user_id}/evidence", json=payload_canonical, headers=headers)
    assert res_a.status_code in [200, 201], f"Canonical submission failed: {res_a.text}"
    ev_a = res_a.json()
    assert ev_a["skill_id"] == "SK_CAN"
    print(f"\n[PASS] Step 2A Submit Evidence (Canonical): Successfully submitted {ev_a['skill_id']}")

    # Submission B: with skill name (e.g. "CAN Bus" or "Battery Management Systems")
    payload_name = {
        "skill_id": "CAN Bus",
        "evidence_type": "project",
        "strength": "intermediate",
        "metadata": {
            "repo": "https://github.com/worknexus/can-bus-gui",
            "notes": "Submitted with skill name"
        }
    }
    res_b = client.post(f"/api/v1/students/{user_id}/evidence", json=payload_name, headers=headers)
    assert res_b.status_code in [200, 201], f"Skill name submission failed: {res_b.text}"
    ev_b = res_b.json()
    assert ev_b["skill_id"] == "SK_CAN", f"Expected canonical 'SK_CAN', got '{ev_b['skill_id']}'"
    print(f"\n[PASS] Step 2B Submit Evidence (Skill Name 'CAN Bus'): Resolved to canonical {ev_b['skill_id']}")


def test_03_view_evidence_history(client, student_auth):
    """Workflow Step 3: View Evidence History"""
    user_id = student_auth["user_id"]
    headers = student_auth["headers"]

    # Ensure evidence is submitted in this transaction boundary
    payload = {
        "skill_id": "SK_CAN",
        "evidence_type": "project",
        "strength": "advanced",
        "metadata": {"repo": "https://github.com/worknexus/can-bus-driver"}
    }
    sub_res = client.post(f"/api/v1/students/{user_id}/evidence", json=payload, headers=headers)
    assert sub_res.status_code in [200, 201]

    response = client.get(f"/api/v1/students/{user_id}/evidence", headers=headers)
    assert response.status_code == 200, f"Evidence list failed: {response.text}"
    evidence_list = response.json()

    assert isinstance(evidence_list, list)
    assert len(evidence_list) >= 1
    # Check that canonical skill IDs are returned, not raw integer primary keys
    for item in evidence_list:
        assert isinstance(item["skill_id"], str)
        assert not item["skill_id"].isdigit(), f"Found integer string '{item['skill_id']}' instead of canonical ID"
        assert item["skill_id"].startswith("SK_") or len(item["skill_id"]) > 2

    print(f"\n[PASS] Step 3 View Evidence History: Retrieved {len(evidence_list)} evidence artifacts, all canonical")


def test_04_view_curriculum_recommendations(client, student_auth):
    """Workflow Step 4: View Curriculum Recommendations"""
    user_id = student_auth["user_id"]
    headers = student_auth["headers"]
    role_id = "ROLE_EV_TECHNICIAN"

    response = client.get(f"/api/v1/ml/students/{user_id}/course-candidates/{role_id}?mode=live", headers=headers)
    assert response.status_code == 200, f"Course candidates failed: {response.text}"
    data = response.json()

    candidates = data.get("candidate_courses", [])
    print(f"\n[PASS] Step 4 View Curriculum Recommendations: Retrieved {len(candidates)} candidate courses for {role_id}")
    assert len(candidates) > 0, f"Expected candidate courses to bridge role gaps, got 0. Response: {data}"

    # Verify candidate properties
    first_candidate = candidates[0]
    assert "course_id" in first_candidate
    assert "title" in first_candidate or "course_name" in first_candidate
    skills_covered = first_candidate.get("skills_covered", first_candidate.get("covered_personalized_skills", []))
    assert len(skills_covered) > 0
    for sk in skills_covered:
        assert isinstance(sk, str)
        assert not sk.isdigit(), f"Taught skill '{sk}' should be canonical string, not digit"
    print(f"       Course: {first_candidate.get('title') or first_candidate.get('course_name')} (ID: {first_candidate['course_id']}) covers {skills_covered}")
