import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from ..models.skills import Skill as SqlSkill
from ..models.student_roles import (
    TargetRole as SqlTargetRole,
    RoleSkill as SqlRoleSkill,
    StudentProfile as SqlStudentProfile,
    StudentSkillEvidence as SqlStudentEvidence,
)
from ..models.users import User as SqlUser
from ..models.courses import Course as SqlCourse
from ..models.course_skills import CourseSkill as SqlCourseSkill
from ..models.employers import Employer as SqlEmployer
from ..auth.security import hash_password


def _find_ml_data_dir() -> Path:
    # 1. Repo root relative to backend/app/db/seed.py
    candidate1 = Path(__file__).resolve().parent.parent.parent.parent / "ml" / "data"
    if candidate1.exists():
        return candidate1
    # 2. Container root /app/ml/data
    candidate2 = Path("/app/ml/data")
    if candidate2.exists():
        return candidate2
    # 3. Backend parent /ml/data
    candidate3 = Path(__file__).resolve().parent.parent.parent / "ml" / "data"
    if candidate3.exists():
        return candidate3
    return candidate1


ML_DATA_DIR = _find_ml_data_dir()
SKILLS_PATH = ML_DATA_DIR / "skills.json"
SAMPLE_ROLES_PATH = ML_DATA_DIR / "sample_role_contexts.json"
SAMPLE_STUDENTS_PATH = ML_DATA_DIR / "sample_student_profiles.json"
SAMPLE_ASSIGNMENTS_PATH = ML_DATA_DIR / "sample_student_role_assignments.json"
SAMPLE_COURSES_PATH = ML_DATA_DIR / "sample_courses.json"


def _is_mock(db) -> bool:
    return hasattr(db, "target_roles") and hasattr(db, "student_profiles")


def seed_canonical_employers(db) -> int:
    """
    Seed default benchmark employer.
    """
    is_mock = _is_mock(db)
    if is_mock:
        if 1 not in getattr(db, "employers", {}):
            db.add(SqlEmployer(id=1, company_name="Main EV Corp", trust_weight=1.0, user_id=1))
            return 1
        return 0
    else:
        existing = db.query(SqlEmployer).filter(SqlEmployer.id == 1).first()
        if not existing:
            # Check if an employer user exists, or create parent employer user first
            emp_user = db.query(SqlUser).filter(SqlUser.id == 1, SqlUser.role.ilike("employer")).first()
            if not emp_user:
                emp_user = db.query(SqlUser).filter(SqlUser.role.ilike("employer")).first()
            if not emp_user:
                # Check if user with id=1 already exists for a different role
                user_1 = db.query(SqlUser).filter(SqlUser.id == 1).first()
                if not user_1:
                    emp_user = SqlUser(
                        id=1,
                        email="employer@worknexus.io",
                        hashed_password=hash_password("SecurePassword123!"),
                        full_name="Main EV Corp",
                        role="employer",
                        is_active=True
                    )
                else:
                    emp_user = SqlUser(
                        email="employer@worknexus.io",
                        hashed_password=hash_password("SecurePassword123!"),
                        full_name="Main EV Corp",
                        role="employer",
                        is_active=True
                    )
                db.add(emp_user)
                db.flush()

            # Ensure this user doesn't already have another employer profile
            existing_user_emp = db.query(SqlEmployer).filter(SqlEmployer.user_id == emp_user.id).first()
            if not existing_user_emp:
                db.add(SqlEmployer(id=1, company_name="Main EV Corp", trust_weight=1.0, user_id=emp_user.id))
                db.commit()
                return 1
            return 0
        return 0


def seed_canonical_skills(db) -> int:
    """
    Seed canonical taxonomy skills from ml/data/skills.json.
    """
    if not SKILLS_PATH.exists():
        return 0

    with open(SKILLS_PATH, "r", encoding="utf-8") as f:
        skills_data = json.load(f)

    count = 0
    is_mock = _is_mock(db)

    for s in skills_data:
        s_id = s["id"]
        if is_mock:
            if s_id not in db.skills:
                skill = SqlSkill(
                    skill_id=s_id,
                    name=s["name"],
                    category=s["category"],
                    version=int(s.get("version", 1))
                )
                db.add(skill)
                count += 1
        else:
            existing = db.query(SqlSkill).filter(SqlSkill.skill_id == s_id).first()
            if not existing:
                skill = SqlSkill(
                    skill_id=s_id,
                    name=s["name"],
                    category=s["category"],
                    description=s.get("description", ", ".join(s.get("aliases", []))),
                    is_active=True
                )
                db.add(skill)
                count += 1

    db.commit()
    return count


def seed_benchmark_roles(db) -> Dict[str, int]:
    """
    Seed 5 synthetic benchmark career roles and their exact Phase 6B required skills.
    """
    seed_canonical_skills(db)

    benchmark_roles = [
        {
            "id": "ROLE_DATA_ENGINEER",
            "name": "Data Engineer",
            "description": "Benchmark Role: Builds data pipelines, ETL workflows, and cloud data architecture.",
            "skills": ["SK_PYTHON", "SK_SQL", "SK_AIRFLOW", "SK_SPARK", "SK_AWS"]
        },
        {
            "id": "ROLE_EV_TECHNICIAN",
            "name": "EV Technician",
            "description": "Benchmark Role: Diagnoses, maintains, and repairs EV battery systems and powertrain electronics.",
            "skills": ["SK_BMS", "SK_CAN", "SK_BATTERY_CELL", "SK_DIAG", "SK_HIGH_VOLTAGE", "SK_THERMAL"]
        },
        {
            "id": "ROLE_FULL_STACK_DEV",
            "name": "Full Stack Developer",
            "description": "Benchmark Role: Develops responsive frontend UIs and scalable backend API services.",
            "skills": ["SK_PYTHON", "SK_JAVASCRIPT", "SK_REACT", "SK_SQL", "SK_GIT", "SK_DOCKER"]
        },
        {
            "id": "ROLE_HEALTHCARE_ASST",
            "name": "Healthcare Assistant",
            "description": "Benchmark Role: Provides clinical support, basic life support, and electronic health records maintenance.",
            "skills": ["SK_CPR_BLS", "SK_FIRST_AID", "SK_PATIENT_CARE", "SK_VITAL_SIGNS", "SK_EHR"]
        },
        {
            "id": "ROLE_INDUSTRIAL_AUTO",
            "name": "Industrial Automation Specialist",
            "description": "Benchmark Role: Programs PLCs, configures SCADA systems, and installs control panel wiring.",
            "skills": ["SK_PLC", "SK_SCADA", "SK_PANEL_WIRING", "SK_CIRCUIT_DESIGN"]
        }
    ]

    roles_seeded = 0
    role_skills_seeded = 0
    is_mock = _is_mock(db)

    for r_data in benchmark_roles:
        r_id = r_data["id"]

        if is_mock:
            role = db.target_roles.get(r_id)
            if not role:
                role = SqlTargetRole(
                    id=r_id,
                    name=r_data["name"],
                    description=r_data["description"],
                    is_active=True
                )
                db.add(role)
                roles_seeded += 1

            for sk_id in r_data["skills"]:
                if sk_id not in db.skills:
                    raise ValueError(f"Cannot map skill '{sk_id}' to role '{r_id}': skill not found in canonical taxonomy.")
                if not any(rs.role_id == r_id and rs.skill_id == sk_id for rs in db.role_skills):
                    rs = SqlRoleSkill(id=None, role_id=r_id, skill_id=sk_id)
                    db.add(rs)
                    role_skills_seeded += 1
        else:
            role = db.query(SqlTargetRole).filter(SqlTargetRole.id == r_id).first()
            if not role:
                role = SqlTargetRole(
                    id=r_id,
                    name=r_data["name"],
                    description=r_data["description"],
                    is_active=True
                )
                db.add(role)
                db.flush()
                roles_seeded += 1

            for sk_id in r_data["skills"]:
                sk_obj = db.query(SqlSkill).filter(SqlSkill.skill_id == sk_id).first()
                if not sk_obj:
                    continue
                link = db.query(SqlRoleSkill).filter(
                    SqlRoleSkill.role_id == r_id,
                    SqlRoleSkill.skill_id == sk_obj.id
                ).first()
                if not link:
                    db.add(SqlRoleSkill(role_id=r_id, skill_id=sk_obj.id))
                    role_skills_seeded += 1

    db.commit()
    return {"roles_seeded": roles_seeded, "role_skills_seeded": role_skills_seeded}


def seed_canonical_courses(db) -> Dict[str, int]:
    """
    Seed standard curriculum courses and their taught skills.
    """
    if not SAMPLE_COURSES_PATH.exists():
        return {"courses_seeded": 0}

    with open(SAMPLE_COURSES_PATH, "r", encoding="utf-8") as f:
        courses_data = json.load(f)

    courses_seeded = 0
    is_mock = _is_mock(db)

    for c in courses_data:
        cid = int(c["course_id"])
        c_code = f"COURSE-{cid}"
        c_name = c["name"]
        dept = c.get("role", "Vocational Studies")
        desc = f"Comprehensive curriculum for {c_name} covering verified industry competencies."

        if is_mock:
            if cid not in db.courses:
                course = SqlCourse(id=cid, course_id=c_code, name=c_name, department=dept, description=desc)
                db.add(course)
                courses_seeded += 1
            for sk_id in c.get("skill_ids", []):
                if not any(cs.course_id == cid and getattr(cs, "skill_id", None) == sk_id for cs in db.course_skills):
                    db.add(SqlCourseSkill(course_id=cid, skill_id=sk_id, coverage_pct=float(c.get("coverage", {}).get(sk_id, 100.0))))
        else:
            existing = db.query(SqlCourse).filter(
                (SqlCourse.id == cid) | (SqlCourse.course_id == c_code)
            ).first()
            if not existing:
                course = SqlCourse(
                    id=cid,
                    course_id=c_code,
                    name=c_name,
                    department=dept,
                    description=desc,
                    is_active=True
                )
                db.add(course)
                db.flush()
                courses_seeded += 1
            else:
                course = existing

            for sk_id in c.get("skill_ids", []):
                sk_obj = db.query(SqlSkill).filter(SqlSkill.skill_id == sk_id).first()
                if sk_obj:
                    link = db.query(SqlCourseSkill).filter(
                        SqlCourseSkill.course_id == course.id,
                        SqlCourseSkill.skill_id == sk_obj.id
                    ).first()
                    if not link:
                        db.add(SqlCourseSkill(course_id=course.id, skill_id=sk_obj.id))

    db.commit()
    return {"courses_seeded": courses_seeded}


def seed_demo_students(db) -> Dict[str, int]:
    """
    Seed demo/benchmark student profiles and evidence for STU_001 - STU_005.
    """
    if not (SAMPLE_STUDENTS_PATH.exists() and SAMPLE_ASSIGNMENTS_PATH.exists()):
        return {"students_seeded": 0, "evidence_records_seeded": 0}

    with open(SAMPLE_STUDENTS_PATH, "r", encoding="utf-8") as f:
        students_data = json.load(f)

    with open(SAMPLE_ASSIGNMENTS_PATH, "r", encoding="utf-8") as f:
        assignments_data = json.load(f)

    raw_assigns = assignments_data.get("assignments", assignments_data) if isinstance(assignments_data, dict) else assignments_data
    assignments_map = {a["student_id"]: a.get("role_id", a.get("assigned_role_id")) for a in raw_assigns}

    students_seeded = 0
    evidence_seeded = 0
    is_mock = _is_mock(db)

    for idx, stu in enumerate(students_data, 1):
        stu_str_id = stu["student_id"]
        user_id = 1000 + idx
        role_id = assignments_map.get(stu_str_id, "ROLE_FULL_STACK_DEV")

        if is_mock:
            user = db.users.get(user_id)
            if not user:
                user = SqlUser(id=user_id, email=f"{stu_str_id.lower()}@demo.worknexus.org", role="student")
                db.add(user)

            profile = next((p for p in db.student_profiles.values() if p.user_id == user_id), None)
            if not profile:
                profile = SqlStudentProfile(id=idx, user_id=user_id, target_role_id=role_id)
                db.add(profile)
                students_seeded += 1

            for sk_entry in stu.get("skills", []):
                sk_id = sk_entry["skill_id"]
                ev_list = sk_entry.get("evidence", [{"evidence_type": "self_reported", "evidence_strength": "intermediate"}])
                for ev in ev_list:
                    ev_type = ev.get("evidence_type", "self_reported")
                    strength = ev.get("evidence_strength", "intermediate")
                    metadata = {k: v for k, v in ev.items() if k not in ["evidence_type", "evidence_strength"]}
                    evidence = SqlStudentEvidence(
                        id=None,
                        student_profile_id=profile.id,
                        skill_id=sk_id,
                        evidence_type=ev_type,
                        strength=strength,
                        metadata=metadata
                    )
                    db.add(evidence)
                    evidence_seeded += 1
        else:
            user = db.query(SqlUser).filter(SqlUser.id == user_id).first()
            if not user:
                user = SqlUser(
                    id=user_id,
                    email=f"{stu_str_id.lower()}@demo.worknexus.org",
                    hashed_password=hash_password("DemoPassword123!"),
                    full_name=f"Demo Student {idx}",
                    role="student",
                    is_active=True
                )
                db.add(user)
                db.flush()

            profile = db.query(SqlStudentProfile).filter(SqlStudentProfile.user_id == user_id).first()
            if not profile:
                profile = SqlStudentProfile(
                    user_id=user.id,
                    target_role_id=role_id
                )
                db.add(profile)
                db.flush()
                students_seeded += 1

            for sk_entry in stu.get("skills", []):
                sk_id = sk_entry["skill_id"]
                sk_obj = db.query(SqlSkill).filter(SqlSkill.skill_id == sk_id).first()
                if not sk_obj:
                    continue
                ev_list = sk_entry.get("evidence", [{"evidence_type": "self_reported", "evidence_strength": "intermediate"}])
                for ev in ev_list:
                    ev_type = ev.get("evidence_type", "project")
                    strength = ev.get("evidence_strength", "intermediate")
                    metadata = {k: v for k, v in ev.items() if k not in ["evidence_type", "evidence_strength"]}
                    db.add(SqlStudentEvidence(
                        student_profile_id=profile.id,
                        skill_id=sk_obj.id,
                        evidence_type=ev_type,
                        strength=strength,
                        metadata_=metadata
                    ))
                    evidence_seeded += 1

    db.commit()
    return {"students_seeded": students_seeded, "evidence_records_seeded": evidence_seeded}


def seed_portal_accounts(db) -> Dict[str, int]:
    """
    Seed standard portal demo accounts matching frontend quick-fill credentials:
    - student@worknexus.io (Role: Student)
    - employer@worknexus.io (Role: Employer)
    - institute@worknexus.io (Role: Institute)
    - trainer@worknexus.io (Role: Trainer)
    - admin@worknexus.io (Role: Admin)
    """
    demo_users = [
        {"email": "student@worknexus.io", "name": "Alex Student", "role": "student"},
        {"email": "employer@worknexus.io", "name": "Elena Employer", "role": "employer"},
        {"email": "institute@worknexus.io", "name": "Irene Institute", "role": "institute"},
        {"email": "trainer@worknexus.io", "name": "Trevor Trainer", "role": "trainer"},
        {"email": "admin@worknexus.io", "name": "Arthur Admin", "role": "admin"},
    ]
    is_mock = _is_mock(db)
    seeded = 0
    for u in demo_users:
        if is_mock:
            user = next((x for x in getattr(db, "users", {}).values() if getattr(x, "email", None) == u["email"]), None)
            if not user:
                user = SqlUser(id=len(getattr(db, "users", {})) + 200, email=u["email"], role=u["role"])
                user.full_name = u["name"]
                user.is_active = True
                db.add(user)
                seeded += 1
                if u["role"].lower() == "student" and hasattr(db, "student_profiles"):
                    p = SqlStudentProfile(id=len(db.student_profiles) + 200, user_id=user.id, target_role_id="ROLE_FULL_STACK_DEV")
                    db.add(p)
                elif u["role"].lower() == "employer" and hasattr(db, "employers"):
                    emp = next((e for e in getattr(db, "employers", {}).values() if getattr(e, "user_id", None) == user.id), None)
                    if not emp:
                        emp_id = len(db.employers) + 1
                        db.add(SqlEmployer(id=emp_id, company_name="NexusTech Labs", trust_weight=1.0, user_id=user.id))
        else:
            user = db.query(SqlUser).filter(SqlUser.email == u["email"]).first()
            if not user:
                user = SqlUser(
                    email=u["email"],
                    hashed_password=hash_password("SecurePassword123!"),
                    full_name=u["name"],
                    role=u["role"],
                    is_active=True
                )
                db.add(user)
                db.flush()
                seeded += 1
                if u["role"].lower() == "student":
                    existing_p = db.query(SqlStudentProfile).filter(SqlStudentProfile.user_id == user.id).first()
                    if not existing_p:
                        db.add(SqlStudentProfile(user_id=user.id, target_role_id="ROLE_FULL_STACK_DEV"))
                elif u["role"].lower() == "employer":
                    existing_emp = db.query(SqlEmployer).filter(
                        (SqlEmployer.user_id == user.id) | (SqlEmployer.company_name == "NexusTech Labs")
                    ).first()
                    if not existing_emp:
                        db.add(SqlEmployer(company_name="NexusTech Labs", user_id=user.id, trust_weight=1.0))
                    elif existing_emp.user_id is None:
                        existing_emp.user_id = user.id
            else:
                user.hashed_password = hash_password("SecurePassword123!")
                user.is_active = True
                if u["role"].lower() == "student":
                    existing_p = db.query(SqlStudentProfile).filter(SqlStudentProfile.user_id == user.id).first()
                    if not existing_p:
                        db.add(SqlStudentProfile(user_id=user.id, target_role_id="ROLE_FULL_STACK_DEV"))
                elif u["role"].lower() == "employer":
                    existing_emp = db.query(SqlEmployer).filter(
                        (SqlEmployer.user_id == user.id) | (SqlEmployer.company_name == "NexusTech Labs")
                    ).first()
                    if not existing_emp:
                        db.add(SqlEmployer(company_name="NexusTech Labs", user_id=user.id, trust_weight=1.0))
                    elif existing_emp.user_id is None:
                        existing_emp.user_id = user.id
    if not is_mock:
        db.commit()
    return {"portal_users_seeded": seeded}


def verify_and_heal_profiles(db) -> Dict[str, Any]:
    """
    Ensure all users in the database have their appropriate profile records linked,
    preventing any runtime foreign key or missing-profile failures.
    """
    if _is_mock(db):
        from ..services.employer_service import EmployerService
        emp_res = EmployerService.verify_employer_profiles(db)
        return {"profiles_healed": 0, "healed_employers": emp_res.get("healed_employers", 0)}

    healed_students = 0
    healed_employers = 0

    try:
        # 1. Heal Students
        students = db.query(SqlUser).filter(SqlUser.role.ilike("student")).all()
        for s in students:
            profile = db.query(SqlStudentProfile).filter(SqlStudentProfile.user_id == s.id).first()
            if not profile:
                db.add(SqlStudentProfile(user_id=s.id, target_role_id="ROLE_FULL_STACK_DEV"))
                healed_students += 1
        db.commit()

        # 2. Heal Employers with canonical EmployerService audit
        from ..services.employer_service import EmployerService
        emp_audit = EmployerService.verify_employer_profiles(db)
        healed_employers = emp_audit.get("healed_employers", 0)

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Error during profile verification and healing: {e}")
        if hasattr(db, "rollback"):
            db.rollback()

    return {"healed_students": healed_students, "healed_employers": healed_employers}


def seed_all(db) -> Dict[str, Any]:
    """
    Seed all canonical skills, benchmark roles, courses, demo student profiles, benchmark employer, and demo portal accounts.
    """
    emp_res = seed_canonical_employers(db)
    skills_count = seed_canonical_skills(db)
    roles_res = seed_benchmark_roles(db)
    courses_res = seed_canonical_courses(db)
    students_res = seed_demo_students(db)
    portal_res = seed_portal_accounts(db)
    heal_res = verify_and_heal_profiles(db)
    return {
        "employers_seeded": emp_res,
        "skills_seeded": skills_count,
        **roles_res,
        **courses_res,
        **students_res,
        **portal_res,
        **heal_res
    }

