import pytest
from app.db.session import SessionLocal, MockDatabaseSession
from app.models.users import User
from app.models.student_roles import StudentProfile, StudentSkillEvidence, TargetRole
from app.models.skills import Skill
from app.services.ml_data_service import MLDataService


def test_student_profile_resolution_precedence_sql():
    """
    Regression Test (SQL branch):
    Ensure that when user_id and profile_id overlap (e.g., student user_id=2 and
    seeded demo profile id=2 for user_id=1002), MLDataService.get_live_student_data(db, 2)
    correctly resolves user_id=2 rather than the demo profile id=2.
    Also verifies:
    1. STU_001 resolves to the demo profile (user_id=1001, profile_id=1).
    2. A numeric id that only exists as a profile_id (and not as any user_id)
       correctly resolves via the profile.id fallback.
    """
    db = SessionLocal()
    try:
        # 1. Ensure TargetRole exists
        role = db.query(TargetRole).filter(TargetRole.id == "ROLE_DATA_ENGINEER").first()
        if not role:
            role = TargetRole(
                id="ROLE_DATA_ENGINEER",
                name="Data Engineer",
                description="Data Engineering role",
                is_active=True
            )
            db.add(role)
            db.commit()

        # 2. Ensure Skill exists
        skill = db.query(Skill).filter(Skill.skill_id == "SK_AIRFLOW").first()
        if not skill:
            skill = Skill(
                id=901,
                skill_id="SK_AIRFLOW",
                name="Apache Airflow",
                category="Data Engineering"
            )
            db.add(skill)
            db.commit()

        # 3. Ensure demo profiles with ids 1-5 exist (user_ids 1001-1005)
        for i in range(1, 6):
            demo_uid = 1000 + i
            demo_user = db.query(User).filter(User.id == demo_uid).first()
            if not demo_user:
                demo_user = User(
                    id=demo_uid,
                    email=f"demo_{demo_uid}@worknexus.org",
                    hashed_password="hash",
                    full_name=f"Demo Student {i}",
                    role="student"
                )
                db.add(demo_user)
                db.commit()

            demo_profile = db.query(StudentProfile).filter(StudentProfile.id == i).first()
            if not demo_profile:
                demo_profile = StudentProfile(
                    id=i,
                    user_id=demo_uid,
                    target_role_id="ROLE_EV_TECHNICIAN" if i == 2 else "ROLE_DATA_ENGINEER"
                )
                db.add(demo_profile)
                db.commit()

        # 4. Create real student user with user_id=2
        real_user = db.query(User).filter(User.id == 2).first()
        if not real_user:
            real_user = User(
                id=2,
                email="alex.student@worknexus.io",
                hashed_password="hash",
                full_name="Alex Student",
                role="student"
            )
            db.add(real_user)
            db.commit()

        # Create or update profile for user_id=2 with a distinct profile id (e.g. 34)
        real_profile = db.query(StudentProfile).filter(StudentProfile.user_id == 2).first()
        if not real_profile:
            real_profile = StudentProfile(
                id=34,
                user_id=2,
                target_role_id="ROLE_DATA_ENGINEER"
            )
            db.add(real_profile)
            db.commit()
            db.refresh(real_profile)

        assert real_profile.id != real_profile.user_id, "Profile ID must differ from User ID for regression test"

        # 5. Add evidence for SK_AIRFLOW to real student's profile
        existing_ev = db.query(StudentSkillEvidence).filter(
            StudentSkillEvidence.student_profile_id == real_profile.id,
            StudentSkillEvidence.skill_id == skill.id
        ).first()
        if not existing_ev:
            ev = StudentSkillEvidence(
                student_profile_id=real_profile.id,
                skill_id=skill.id,
                evidence_type="project",
                strength="advanced",
                status="verified",
                is_verified=True,
                metadata_={"notes": "Airflow pipeline project"}
            )
            db.add(ev)
            db.commit()

        # --- Assertions ---
        # A. Resolving student_id=2 MUST resolve to real student (user_id=2), NOT demo profile id=2 (user_id=1002)
        res_2 = MLDataService.get_live_student_data(db, 2)
        assert res_2 is not None, "get_live_student_data(db, 2) must not return None"
        assert res_2["user_id"] == 2, f"Expected user_id=2, got {res_2['user_id']} (wrong profile picked!)"
        assert res_2["profile_id"] == real_profile.id, f"Expected profile_id={real_profile.id}, got {res_2['profile_id']}"
        ev_skills = [e["skill_id"] for e in res_2.get("evidence_records", [])]
        assert "SK_AIRFLOW" in ev_skills, f"Expected 'SK_AIRFLOW' in evidence_records, got {ev_skills}"

        # B. Resolving string '2' must also resolve user_id=2
        res_str_2 = MLDataService.get_live_student_data(db, "2")
        assert res_str_2 is not None
        assert res_str_2["user_id"] == 2
        assert res_str_2["profile_id"] == real_profile.id

        # C. STU_001 demo convention must still resolve to demo profile (profile_id=1, user_id=1001)
        res_stu1 = MLDataService.get_live_student_data(db, "STU_001")
        assert res_stu1 is not None
        assert res_stu1["user_id"] == 1001
        assert res_stu1["profile_id"] == 1

        # D. Fallback resolution: A numeric id that is only a profile id (e.g., profile id 5 where no user has user_id=5)
        # Ensure user_id=5 doesn't exist or test with an explicit orphan profile
        user_5 = db.query(User).filter(User.id == 5).first()
        if not user_5:
            res_5 = MLDataService.get_live_student_data(db, 5)
            assert res_5 is not None
            assert res_5["profile_id"] == 5
            assert res_5["user_id"] == 1005
        else:
            # Create a profile with high ID that is definitely not a user_id
            high_profile = db.query(StudentProfile).filter(StudentProfile.id == 9999).first()
            if not high_profile:
                high_profile = StudentProfile(
                    id=9999,
                    user_id=1001,
                    target_role_id="ROLE_DATA_ENGINEER"
                )
                db.add(high_profile)
                db.commit()
            res_fallback = MLDataService.get_live_student_data(db, 9999)
            assert res_fallback is not None
            assert res_fallback["profile_id"] == 9999
    finally:
        db.close()


def test_student_profile_resolution_precedence_mock():
    """
    Regression Test (MockDatabaseSession branch):
    Ensure that mock session precedence prioritizes user_id over profile.id,
    and falls back to profile.id when no user_id matches.
    """
    mock_db = MockDatabaseSession()

    from app.models.student_roles import StudentProfile as EntityStudentProfile, StudentSkillEvidence as EntityStudentEvidence

    # Seed demo profiles 1-5 with user_ids 1001-1005
    for i in range(1, 6):
        mock_db.student_profiles[i] = EntityStudentProfile(
            id=i,
            user_id=1000 + i,
            target_role_id="ROLE_EV_TECHNICIAN" if i == 2 else "ROLE_DATA_ENGINEER"
        )

    # Add real student profile with id=34, user_id=2
    mock_db.student_profiles[34] = EntityStudentProfile(
        id=34,
        user_id=2,
        target_role_id="ROLE_DATA_ENGINEER"
    )

    # Add evidence for student 2 (profile 34)
    mock_db.student_skill_evidence.append(
        EntityStudentEvidence(
            id=101,
            student_profile_id=34,
            skill_id="SK_AIRFLOW",
            evidence_type="project",
            strength="advanced",
            status="verified",
            is_verified=True,
            metadata={"notes": "Airflow project"}
        )
    )

    # 1. Number 2 must resolve to user_id=2, profile_id=34 (not profile_id=2)
    res = MLDataService.get_live_student_data(mock_db, 2)
    assert res is not None
    assert res["user_id"] == 2
    assert res["profile_id"] == 34
    ev_skills = [e["skill_id"] for e in res["evidence_records"]]
    assert "SK_AIRFLOW" in ev_skills

    # 2. STU_001 must resolve to demo profile id 1, user 1001
    res_stu1 = MLDataService.get_live_student_data(mock_db, "STU_001")
    assert res_stu1 is not None
    assert res_stu1["user_id"] == 1001
    assert res_stu1["profile_id"] == 1

    # 3. Fallback: id 5 where no user has user_id=5 must resolve to profile_id=5
    res_5 = MLDataService.get_live_student_data(mock_db, 5)
    assert res_5 is not None
    assert res_5["profile_id"] == 5
    assert res_5["user_id"] == 1005
