import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from ..models.entities import Skill, TargetRole, RoleSkill, User, StudentProfile, StudentSkillEvidence

SKILLS_PATH = Path(__file__).resolve().parent.parent.parent.parent / "ml" / "data" / "skills.json"
SAMPLE_ROLES_PATH = Path(__file__).resolve().parent.parent.parent.parent / "ml" / "data" / "sample_role_contexts.json"
SAMPLE_STUDENTS_PATH = Path(__file__).resolve().parent.parent.parent.parent / "ml" / "data" / "sample_student_profiles.json"
SAMPLE_ASSIGNMENTS_PATH = Path(__file__).resolve().parent.parent.parent.parent / "ml" / "data" / "sample_student_role_assignments.json"

def seed_canonical_skills(db) -> int:
    """
    Seed canonical taxonomy skills from ml/data/skills.json.
    """
    if not SKILLS_PATH.exists():
        raise FileNotFoundError(f"Canonical skills.json missing at {SKILLS_PATH}")

    with open(SKILLS_PATH, "r", encoding="utf-8") as f:
        skills_data = json.load(f)

    count = 0
    for s in skills_data:
        s_id = s["id"]
        # Check if skill exists
        existing = None
        if hasattr(db, "skills") and s_id in db.skills:
            existing = db.skills[s_id]
        elif hasattr(db, "query"):
            existing = db.query(Skill).filter(lambda x: x.id == s_id).first()

        if not existing:
            skill = Skill(
                id=s_id,
                name=s["name"],
                category=s["category"],
                version=int(s.get("version", 1))
            )
            db.add(skill)
            count += 1

    db.commit()
    return count

def seed_benchmark_roles(db) -> Dict[str, int]:
    """
    Seed 5 synthetic benchmark career roles and their exact Phase 6B required skills.
    Labeled explicitly as benchmark demonstration data.
    """
    # 1. Ensure skills are seeded first
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

    for r_data in benchmark_roles:
        r_id = r_data["id"]
        
        # Check if role exists
        role = None
        if hasattr(db, "target_roles") and r_id in db.target_roles:
            role = db.target_roles[r_id]
        elif hasattr(db, "query"):
            role = db.query(TargetRole).filter(lambda x: x.id == r_id).first()

        if not role:
            role = TargetRole(
                id=r_id,
                name=r_data["name"],
                description=r_data["description"],
                is_active=True
            )
            db.add(role)
            roles_seeded += 1

        # Seed role skills
        for sk_id in r_data["skills"]:
            # Verify skill exists in taxonomy
            existing_skill = None
            if hasattr(db, "skills") and sk_id in db.skills:
                existing_skill = db.skills[sk_id]
            elif hasattr(db, "query"):
                existing_skill = db.query(Skill).filter(lambda x: x.id == sk_id).first()

            if not existing_skill:
                raise ValueError(f"Cannot map skill '{sk_id}' to role '{r_id}': skill not found in canonical taxonomy.")

            # Check if role-skill link exists
            link_exists = False
            if hasattr(db, "role_skills"):
                link_exists = any(rs.role_id == r_id and rs.skill_id == sk_id for rs in db.role_skills)
            elif hasattr(db, "query"):
                link_exists = bool(db.query(RoleSkill).filter(lambda rs: rs.role_id == r_id and rs.skill_id == sk_id).first())

            if not link_exists:
                rs = RoleSkill(id=None, role_id=r_id, skill_id=sk_id)
                db.add(rs)
                role_skills_seeded += 1

    db.commit()
    return {"roles_seeded": roles_seeded, "role_skills_seeded": role_skills_seeded}

def seed_demo_students(db) -> Dict[str, int]:
    """
    Seed demo/benchmark student profiles and evidence for STU_001 - STU_005.
    Explicitly labeled as DEMO/BENCHMARK fixtures.
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

    for idx, stu in enumerate(students_data, 1):
        stu_str_id = stu["student_id"]  # e.g., "STU_001"
        user_id = 1000 + idx
        role_id = assignments_map.get(stu_str_id)

        # 1. Create User if not exists
        user = None
        if hasattr(db, "users") and user_id in db.users:
            user = db.users[user_id]
        elif hasattr(db, "query"):
            user = db.query(User).filter(lambda u: u.id == user_id).first()

        if not user:
            user = User(id=user_id, email=f"{stu_str_id.lower()}@demo.worknexus.org", role="Student")
            db.add(user)

        # 2. Create StudentProfile if not exists
        profile = None
        if hasattr(db, "student_profiles"):
            profile = next((p for p in db.student_profiles.values() if p.user_id == user_id), None)
        elif hasattr(db, "query"):
            profile = db.query(StudentProfile).filter(lambda p: p.user_id == user_id).first()

        if not profile:
            profile = StudentProfile(id=idx, user_id=user_id, target_role_id=role_id)
            db.add(profile)
            students_seeded += 1
            db.flush()

        # 3. Seed Skill Evidence
        for sk_entry in stu.get("skills", []):
            sk_id = sk_entry["skill_id"]
            
            ev_list = []
            if "evidence" in sk_entry and isinstance(sk_entry["evidence"], list):
                ev_list = sk_entry["evidence"]
            elif "evidence_type" in sk_entry:
                ev_list = [{
                    "evidence_type": sk_entry.get("evidence_type", "self_reported"),
                    "evidence_strength": sk_entry.get("evidence_strength", "intermediate")
                }]

            for ev in ev_list:
                ev_type = ev.get("evidence_type", ev.get("type", "self_reported"))
                strength = ev.get("evidence_strength", ev.get("strength", "intermediate"))
                metadata = {k: v for k, v in ev.items() if k not in ["type", "evidence_type", "strength", "evidence_strength"]}

                # Add evidence record
                evidence = StudentSkillEvidence(
                    id=None,
                    student_profile_id=profile.id,
                    skill_id=sk_id,
                    evidence_type=ev_type,
                    strength=strength,
                    metadata=metadata
                )
                db.add(evidence)
                evidence_seeded += 1

    db.commit()
    return {"students_seeded": students_seeded, "evidence_records_seeded": evidence_seeded}

def seed_all(db) -> Dict[str, Any]:
    """
    Seed all canonical skills, benchmark roles, and demo student profiles.
    """
    skills_count = seed_canonical_skills(db)
    roles_res = seed_benchmark_roles(db)
    students_res = seed_demo_students(db)
    return {
        "skills_seeded": skills_count,
        **roles_res,
        **students_res
    }

