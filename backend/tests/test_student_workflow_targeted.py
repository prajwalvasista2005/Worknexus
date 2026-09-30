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


def test_05_evidence_submission_updates_gap_and_match_percentage(client, student_auth):
    """Workflow Step 5: Evidence submission dynamically clears gaps and updates match score"""
    user_id = student_auth["user_id"]
    headers = student_auth["headers"]
    role_id = "ROLE_EV_TECHNICIAN"

    # 1. Fetch initial gap
    init_res = client.get(f"/api/v1/ml/students/{user_id}/gap/{role_id}?mode=live", headers=headers)
    assert init_res.status_code == 200
    init_data = init_res.json()
    init_missing = init_data.get("missing_skills", [])
    init_acquired = init_data.get("acquired_skills", [])
    init_score = init_data.get("overall_match_score", init_data.get("match_score", 0))

    assert len(init_missing) > 0, "Expected missing skills initially"
    target_skill = init_missing[0]
    target_skill_id = target_skill.get("skill_id", target_skill.get("id")) if isinstance(target_skill, dict) else str(target_skill)

    # 2. Submit verified evidence for the missing skill
    payload = {
        "skill_id": target_skill_id,
        "evidence_type": "project",
        "strength": "advanced",
        "metadata": {
            "repo": "https://github.com/worknexus/verified-proof-repo",
            "notes": f"Submitted proof for {target_skill_id}"
        }
    }
    sub_res = client.post(f"/api/v1/students/{user_id}/evidence", json=payload, headers=headers)
    assert sub_res.status_code in [200, 201]

    # 3. Fetch updated gap and verify state synchronization
    updated_res = client.get(f"/api/v1/ml/students/{user_id}/gap/{role_id}?mode=live", headers=headers)
    assert updated_res.status_code == 200
    updated_data = updated_res.json()
    updated_missing = updated_data.get("missing_skills", [])
    updated_acquired = updated_data.get("acquired_skills", [])
    updated_score = updated_data.get("overall_match_score", updated_data.get("match_score", 0))

    assert len(updated_acquired) == len(init_acquired) + 1, "Acquired skills count should increment"
    assert len(updated_missing) == len(init_missing) - 1, "Missing skills count should decrement"
    assert updated_score >= init_score, "Match score should improve after submitting evidence"
    print(f"\n[PASS] Step 5 Dynamic Gap Update: Match score updated from {init_score} to {updated_score}")


def test_06_airflow_evidence_clears_apache_airflow_role_gap(client):
    """
    Workflow Step 6: Canonical skill ID (SK_AIRFLOW) evidence clears
    human-readable target role competency ('Apache Airflow') gap,
    updating match score above 0% and removing it from missing gaps.
    """
    from app.db.session import SessionLocal
    from app.models.users import User
    from app.models.skills import Skill
    from app.models.student_roles import TargetRole, RoleSkill, StudentProfile, StudentSkillEvidence
    from app.auth.security import hash_password
    from app.auth.jwt import create_access_token

    db = SessionLocal()
    try:
        # 1. Setup fresh student user for clean gap baseline
        student_email = "airflow_test_student@worknexus.org"
        user = db.query(User).filter(User.email == student_email).first()
        if not user:
            user = User(
                email=student_email,
                hashed_password=hash_password("Password123!"),
                full_name="Airflow Test Student",
                role="student",
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # 2. Ensure ROLE_DATA_ENGINEER exists with Apache Airflow (SK_AIRFLOW)
        role = db.query(TargetRole).filter(TargetRole.id == "ROLE_DATA_ENGINEER").first()
        if not role:
            role = TargetRole(
                id="ROLE_DATA_ENGINEER",
                name="Data Engineer",
                description="Build scalable data pipelines and distributed storage systems.",
                is_active=True,
            )
            db.add(role)
            db.commit()

        # Ensure SK_AIRFLOW skill exists in database
        skill = db.query(Skill).filter(Skill.skill_id == "SK_AIRFLOW").first()
        if not skill:
            skill = Skill(
                skill_id="SK_AIRFLOW",
                name="Apache Airflow",
                category="IT / Data",
                description="Workflow orchestration tool",
                is_active=True,
            )
            db.add(skill)
            db.commit()
            db.refresh(skill)

        # Ensure RoleSkill links ROLE_DATA_ENGINEER to SK_AIRFLOW
        rs = db.query(RoleSkill).filter(
            RoleSkill.role_id == "ROLE_DATA_ENGINEER",
            RoleSkill.skill_id == skill.id
        ).first()
        if not rs:
            rs = RoleSkill(role_id="ROLE_DATA_ENGINEER", skill_id=skill.id)
            db.add(rs)
            db.commit()

        # Clean any previous evidence for this student to start at 0%
        profile = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
        if not profile:
            profile = StudentProfile(user_id=user.id, target_role_id="ROLE_DATA_ENGINEER")
            db.add(profile)
            db.commit()
            db.refresh(profile)
        else:
            profile.target_role_id = "ROLE_DATA_ENGINEER"
            db.query(StudentSkillEvidence).filter(
                StudentSkillEvidence.student_profile_id == profile.id
            ).delete()
            db.commit()

        token = create_access_token(data={"sub": user.email, "user_id": user.id, "role": "Student"})
        headers = {
            "Authorization": f"Bearer {token}",
            "X-User-Id": str(user.id),
            "X-User-Role": "Student",
            "X-User-Email": user.email,
        }

        # 3. Initial Gap check before evidence submission
        init_res = client.get(f"/api/v1/ml/students/{user.id}/gap/ROLE_DATA_ENGINEER?mode=live", headers=headers)
        assert init_res.status_code == 200, f"Initial gap request failed: {init_res.text}"
        init_data = init_res.json()

        init_missing_names = [
            s.get("name") or s.get("skill_name") or s.get("skill_id")
            for s in init_data.get("missing_skills", [])
        ]
        assert any("airflow" in str(n).lower() for n in init_missing_names), (
            f"Expected Apache Airflow to be in missing skills initially. Got: {init_missing_names}"
        )
        assert init_data.get("overall_match_score", 0.0) == 0.0, "Expected initial match score of 0.0"

        # 4. Submit evidence using canonical skill_id SK_AIRFLOW
        payload = {
            "skill_id": "SK_AIRFLOW",
            "evidence_type": "project",
            "strength": "advanced",
            "metadata": {
                "repo": "https://github.com/worknexus/etl-airflow-dags",
                "notes": "Engineered DAG orchestrator for big data ingestion"
            }
        }
        sub_res = client.post(f"/api/v1/students/{user.id}/evidence", json=payload, headers=headers)
        assert sub_res.status_code in [200, 201], f"Evidence submission failed: {sub_res.text}"

        # 5. Verify that Apache Airflow is marked acquired and match score > 0%
        updated_res = client.get(f"/api/v1/ml/students/{user.id}/gap/ROLE_DATA_ENGINEER?mode=live", headers=headers)
        assert updated_res.status_code == 200, f"Updated gap request failed: {updated_res.text}"
        updated_data = updated_res.json()

        updated_missing_names = [
            s.get("name") or s.get("skill_name") or s.get("skill_id")
            for s in updated_data.get("missing_skills", [])
        ]
        updated_acquired_names = [
            s.get("name") or s.get("skill_name") or s.get("skill_id")
            for s in updated_data.get("acquired_skills", [])
        ]

        # Apache Airflow should no longer be missing
        assert not any("airflow" in str(n).lower() for n in updated_missing_names), (
            f"Apache Airflow should NOT be missing after submitting evidence. Missing: {updated_missing_names}"
        )
        # Apache Airflow should be in acquired skills
        assert any("airflow" in str(n).lower() for n in updated_acquired_names), (
            f"Apache Airflow should be in acquired skills. Acquired: {updated_acquired_names}"
        )
        # Match score must be > 0%
        updated_score = updated_data.get("overall_match_score", updated_data.get("match_score", 0.0))
        assert updated_score > 0.0, f"Expected match score > 0.0, got {updated_score}"
        print(f"\n[PASS] Step 6A SK_AIRFLOW Evidence Cleared Role Gap: Match score rose to {updated_score}")

        # 6. Submit human-readable competency string 'Python Programming' to clear SK_PYTHON
        payload_py = {
            "skill_id": "Python Programming",
            "evidence_type": "project",
            "strength": "advanced",
            "metadata": {
                "repo": "https://github.com/worknexus/data-pipeline-py",
                "notes": "Python pandas and pyarrow pipelines"
            }
        }
        sub_py = client.post(f"/api/v1/students/{user.id}/evidence", json=payload_py, headers=headers)
        assert sub_py.status_code in [200, 201], f"Python evidence submission failed: {sub_py.text}"

        py_res = client.get(f"/api/v1/ml/students/{user.id}/gap/ROLE_DATA_ENGINEER?mode=live", headers=headers)
        assert py_res.status_code == 200
        py_data = py_res.json()

        py_missing_names = [
            s.get("name") or s.get("skill_name") or s.get("skill_id")
            for s in py_data.get("missing_skills", [])
        ]
        py_acquired_names = [
            s.get("name") or s.get("skill_name") or s.get("skill_id")
            for s in py_data.get("acquired_skills", [])
        ]

        assert not any("python" in str(n).lower() for n in py_missing_names), (
            f"Python should NOT be in missing skills. Missing: {py_missing_names}"
        )
        assert any("python" in str(n).lower() for n in py_acquired_names), (
            f"Python should be in acquired skills. Acquired: {py_acquired_names}"
        )
        py_score = py_data.get("overall_match_score", py_data.get("match_score", 0.0))
        assert py_score > updated_score, f"Expected py_score > {updated_score}, got {py_score}"
        print(f"\n[PASS] Step 6B 'Python Programming' Evidence Cleared Role Gap: Match score rose from {updated_score} to {py_score}")
    finally:
        db.close()


def test_07_automatic_profile_skill_upsert_and_cascading_gap_response(client):
    """
    Workflow Step 7: Automatic Profile Skill Upsert on Evidence Submission & Cascading Gap Recalculation
    1. Verifies that when evidence is submitted, the skill is automatically upserted into
       the user_skills / StudentSkill table with proficiency_level and source='Verified Evidence'.
    2. Verifies that the evidence submission response immediately returns the updated
       acquired_skills list, missing_skills list, and recalculated match_score.
    """
    from app.db.session import SessionLocal
    from app.models.users import User
    from app.models.skills import Skill
    from app.models.user_skills import UserSkill
    from app.models.student_roles import TargetRole, RoleSkill, StudentProfile, StudentSkillEvidence
    from app.auth.security import hash_password
    from app.auth.jwt import create_access_token

    db = SessionLocal()
    try:
        email = "cascading_test_student@worknexus.org"
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                email=email,
                hashed_password=hash_password("Password123!"),
                full_name="Cascading Test Student",
                role="student",
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # Ensure ROLE_DATA_ENGINEER and SK_AIRFLOW exist
        role = db.query(TargetRole).filter(TargetRole.id == "ROLE_DATA_ENGINEER").first()
        if not role:
            role = TargetRole(id="ROLE_DATA_ENGINEER", name="Data Engineer", is_active=True)
            db.add(role)
            db.commit()

        skill = db.query(Skill).filter(Skill.skill_id == "SK_AIRFLOW").first()
        if not skill:
            skill = Skill(skill_id="SK_AIRFLOW", name="Apache Airflow", category="IT / Data", is_active=True)
            db.add(skill)
            db.commit()
            db.refresh(skill)

        # Ensure RoleSkill links ROLE_DATA_ENGINEER to SK_AIRFLOW
        rs = db.query(RoleSkill).filter(
            RoleSkill.role_id == "ROLE_DATA_ENGINEER",
            RoleSkill.skill_id == skill.id
        ).first()
        if not rs:
            rs = RoleSkill(role_id="ROLE_DATA_ENGINEER", skill_id=skill.id)
            db.add(rs)
            db.commit()

        # Clear any existing user_skills or evidence for this user to ensure pristine state
        db.query(UserSkill).filter(UserSkill.user_id == user.id).delete()
        profile = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
        if not profile:
            profile = StudentProfile(user_id=user.id, target_role_id="ROLE_DATA_ENGINEER")
            db.add(profile)
            db.commit()
            db.refresh(profile)
        else:
            profile.target_role_id = "ROLE_DATA_ENGINEER"
            db.query(StudentSkillEvidence).filter(
                StudentSkillEvidence.student_profile_id == profile.id
            ).delete()
            db.commit()

        # Verify initial inventory has 0 user_skills
        initial_user_skills = db.query(UserSkill).filter(UserSkill.user_id == user.id).all()
        assert len(initial_user_skills) == 0

        token = create_access_token(data={"sub": user.email, "user_id": user.id, "role": "Student"})
        headers = {
            "Authorization": f"Bearer {token}",
            "X-User-Id": str(user.id),
            "X-User-Role": "Student",
            "X-User-Email": user.email,
        }

        # Submit evidence
        payload = {
            "skill_id": "SK_AIRFLOW",
            "evidence_type": "project",
            "strength": "advanced",
            "metadata": {"repo": "https://github.com/worknexus/cascading-test"}
        }
        res = client.post(f"/api/v1/students/{user.id}/evidence", json=payload, headers=headers)
        assert res.status_code in [200, 201], f"Submission failed: {res.text}"
        data = res.json()

        # 1. Verify response contains cascading gap recalculation fields
        assert "match_score" in data or "overall_match_score" in data
        score = data.get("match_score") if data.get("match_score") is not None else data.get("overall_match_score")
        assert score > 0.0, f"Expected recalculated match_score > 0.0, got {score}"

        assert "acquired_skills" in data or "skills_acquired" in data
        acquired = data.get("acquired_skills") or data.get("skills_acquired")
        assert any("airflow" in str(s.get("name") or s.get("skill_id")).lower() for s in acquired)

        # 2. Verify automatic profile skill upsert in database
        db_user_skill = db.query(UserSkill).filter(
            UserSkill.user_id == user.id,
            UserSkill.skill_id == skill.id
        ).first()
        assert db_user_skill is not None, "Expected UserSkill to be automatically upserted"
        assert db_user_skill.source == "Verified Evidence"
        assert db_user_skill.proficiency_level == "Advanced"

        print(f"\n[PASS] Step 7 Automatic Profile Skill Upsert & Cascading Gap: match_score={score}, source={db_user_skill.source}")
    finally:
        db.close()
