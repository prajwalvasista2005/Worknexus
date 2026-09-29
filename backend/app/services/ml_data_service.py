from typing import Dict, List, Any, Tuple, Optional, Union
from collections import defaultdict

from app.models.job_postings import JobPosting as EntityJobPosting
from app.models.jobSkill import JobSkill as EntityJobSkill
from app.models.courses import Course as EntityCourse
from app.models.course_skills import CourseSkill as EntityCourseSkill
from app.models.employers import (
    Employer as EntityEmployer,
    EmployerFeedback as EntityEmployerFeedback,
    EmployerFeedbackSignal as EntityEmployerFeedbackSignal
)
from app.models.student_roles import (
    TargetRole as EntityTargetRole,
    RoleSkill as EntityRoleSkill,
    StudentProfile as EntityStudentProfile,
    StudentSkillEvidence as EntityStudentSkillEvidence
)
from app.models.users import User as EntityUser

class MLDataService:
    """
    Backend service responsible for preparing live database records into
    pure domain dictionaries for the MLAdapter without N+1 queries.
    Seamlessly supports both SQLAlchemy database sessions and lightweight MockDatabaseSession.
    """

    @staticmethod
    def _is_mock(db) -> bool:
        return hasattr(db, "job_postings") or hasattr(db, "student_profiles")

    @staticmethod
    def get_live_jobs_data(db) -> Tuple[List[Dict[str, Any]], int]:
        """
        Fetch all job postings and their associated skill extractions.
        """
        if MLDataService._is_mock(db):
            all_jobs = list(getattr(db, "job_postings", {}).values())
            all_skills = list(getattr(db, "job_skills", []))
        elif hasattr(db, "query"):
            try:
                from app.models.job_postings import JobPosting as DBJobPosting
                from app.models.jobSkill import JobSkill as DBJobSkill
                all_jobs = db.query(DBJobPosting).all()
                all_skills = db.query(DBJobSkill).all()
            except Exception:
                all_jobs = []
                all_skills = []
        else:
            all_jobs = []
            all_skills = []

        total_jobs_count = len(all_jobs)
        skills_by_job: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for s in all_skills:
            job_id = getattr(s, "job_id", None)
            sk_id = getattr(s, "skill_id", "")
            if hasattr(s, "skill") and s.skill and hasattr(s.skill, "skill_id"):
                sk_id = s.skill.skill_id
            conf = getattr(s, "confidence_score", 1.0)
            if job_id is not None:
                skills_by_job[job_id].append({
                    "skill_id": str(sk_id),
                    "confidence_score": float(conf)
                })

        jobs_list = []
        for j in all_jobs:
            company = getattr(j, "company_name", getattr(j, "company", "WorkNexus Partner"))
            title = getattr(j, "title", "Technical Role")
            location = getattr(j, "location", "Remote") or "Remote"
            jobs_list.append({
                "job_id": str(j.id),
                "title": title,
                "company": company,
                "location": location,
                "source": getattr(j, "source", "worknexus_db") or "worknexus_db",
                "skills": skills_by_job.get(j.id, [])
            })

        return jobs_list, total_jobs_count

    @staticmethod
    def _build_skill_lookup(db) -> Dict[Any, str]:
        """
        Build mapping from integer database ID, string integer ID, and skill_id to canonical skill_id.
        """
        lookup: Dict[Any, str] = {}
        if MLDataService._is_mock(db):
            for s in getattr(db, "skills", {}).values():
                sid = getattr(s, "id", None)
                scode = getattr(s, "skill_id", getattr(s, "id", None))
                if scode:
                    lookup[str(scode)] = str(scode)
                    if sid is not None:
                        lookup[sid] = str(scode)
                        lookup[str(sid)] = str(scode)
                sname = getattr(s, "name", None)
                if sname and scode:
                    lookup[sname] = str(scode)
                    lookup[sname.lower()] = str(scode)
        elif hasattr(db, "query"):
            try:
                from app.models.skills import Skill as DBSkill
                for s in db.query(DBSkill).all():
                    lookup[s.id] = s.skill_id
                    lookup[str(s.id)] = s.skill_id
                    lookup[s.skill_id] = s.skill_id
                    if s.name:
                        lookup[s.name] = s.skill_id
                        lookup[s.name.lower()] = s.skill_id
            except Exception:
                pass
        return lookup

    @staticmethod
    def get_live_courses_data(db) -> List[Dict[str, Any]]:
        """
        Fetch all courses and their taught skills, mapped strictly to canonical skill IDs.
        """
        if MLDataService._is_mock(db):
            all_courses = list(getattr(db, "courses", {}).values())
            all_course_skills = list(getattr(db, "course_skills", []))
        elif hasattr(db, "query"):
            try:
                from app.models.courses import Course as DBCourse
                from app.models.course_skills import CourseSkill as DBCourseSkill
                all_courses = db.query(DBCourse).all()
                all_course_skills = db.query(DBCourseSkill).all()
            except Exception:
                all_courses = []
                all_course_skills = []
        else:
            all_courses = []
            all_course_skills = []

        skill_lookup = MLDataService._build_skill_lookup(db)
        skills_by_course: Dict[int, List[str]] = defaultdict(list)
        for cs in all_course_skills:
            cid = getattr(cs, "course_id", None)
            sk_id = None
            if hasattr(cs, "skill") and cs.skill and hasattr(cs.skill, "skill_id"):
                sk_id = cs.skill.skill_id
            if not sk_id:
                raw_sk = getattr(cs, "skill_id", "")
                sk_id = skill_lookup.get(raw_sk, skill_lookup.get(str(raw_sk), str(raw_sk) if raw_sk else ""))
            if cid is not None and sk_id:
                canonical = skill_lookup.get(sk_id, str(sk_id))
                skills_by_course[cid].append(canonical)

        courses_list = []
        for c in all_courses:
            c_name = getattr(c, "course_title", getattr(c, "title", getattr(c, "name", f"Course {c.id}")))
            courses_list.append({
                "course_id": c.id,
                "course_name": c_name,
                "taught_skills": skills_by_course.get(c.id, [])
            })

        return courses_list

    @staticmethod
    def get_live_employer_feedback_data(db) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Fetch all employer feedback records and detected skill signals.
        """
        if MLDataService._is_mock(db):
            all_fb = list(getattr(db, "employer_feedback", {}).values())
            all_signals = list(getattr(db, "employer_feedback_signals", []))
            all_employers = getattr(db, "employers", {})
        elif hasattr(db, "query"):
            try:
                from app.models.employers import EmployerFeedback, EmployerFeedbackSignal, Employer
                all_fb = db.query(EmployerFeedback).all()
                all_signals = db.query(EmployerFeedbackSignal).all()
                all_employers = {e.id: e for e in db.query(Employer).all()}
            except Exception:
                all_fb = []
                all_signals = []
                all_employers = {}
        else:
            all_fb = []
            all_signals = []
            all_employers = {}

        # Aggregate skill signals across feedback
        signal_agg: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "feedback_count": 0,
            "employers": set(),
            "weighted_signal_sum": 0.0
        })

        for sig in all_signals:
            sk_id = getattr(sig, "skill_id", "")
            fb = next((f for f in all_fb if f.id == getattr(sig, "feedback_id", None)), None)
            emp_id = getattr(fb, "employer_id", None) if fb else None

            signal_agg[sk_id]["feedback_count"] += 1
            if emp_id:
                signal_agg[sk_id]["employers"].add(emp_id)
            signal_agg[sk_id]["weighted_signal_sum"] += getattr(sig, "weighted_signal", 1.0)

        detected_skills = []
        for sk_id, data in sorted(signal_agg.items()):
            detected_skills.append({
                "skill_id": sk_id,
                "feedback_count": data["feedback_count"],
                "unique_employer_count": len(data["employers"]),
                "weighted_signal_sum": round(data["weighted_signal_sum"], 4)
            })

        fb_list = []
        for f in all_fb:
            emp = all_employers.get(f.employer_id) if isinstance(all_employers, dict) else None
            trust = getattr(emp, "trust_weight", 1.0) if emp else 1.0
            fb_list.append({
                "feedback_id": str(f.id),
                "employer_id": f.employer_id,
                "course_id": getattr(f, "course_id", None),
                "trust_weight": trust,
                "comments": getattr(f, "comments", "")
            })

        return fb_list, detected_skills

    @staticmethod
    def get_live_role_data(db, role_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a specific TargetRole and its associated required skills.
        """
        if not role_id:
            return None

        role = None
        skills = []
        skill_lookup = MLDataService._build_skill_lookup(db)

        if MLDataService._is_mock(db):
            if role_id in getattr(db, "target_roles", {}):
                role = db.target_roles[role_id]
                raw_skills = [rs.skill_id for rs in getattr(db, "role_skills", []) if rs.role_id == role.id]
                skills = [skill_lookup.get(s, skill_lookup.get(str(s), str(s))) for s in raw_skills]
        elif hasattr(db, "query"):
            try:
                from app.models.student_roles import TargetRole as DBTargetRole, RoleSkill as DBRoleSkill
                role = db.query(DBTargetRole).filter(DBTargetRole.id == role_id).first()
                if role:
                    role_skills = db.query(DBRoleSkill).filter(DBRoleSkill.role_id == role.id).all()
                    for rs in role_skills:
                        sk_id = None
                        if hasattr(rs, "skill") and rs.skill and hasattr(rs.skill, "skill_id"):
                            sk_id = rs.skill.skill_id
                        if not sk_id:
                            raw_sk = getattr(rs, "skill_id", "")
                            sk_id = skill_lookup.get(raw_sk, skill_lookup.get(str(raw_sk), str(raw_sk) if raw_sk else ""))
                        if sk_id:
                            skills.append(skill_lookup.get(sk_id, str(sk_id)))
            except Exception:
                pass

        if not role:
            return None

        return {
            "role_id": role.id,
            "role_name": getattr(role, "name", role.id),
            "description": getattr(role, "description", None),
            "required_skills": sorted(skills)
        }

    @staticmethod
    def get_live_student_data(db, student_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        Fetch a student profile and all associated skill evidence records.
        Resolves integer user_id / profile_id, or demo 'STU_00X' string IDs.
        Automatically provisions a StudentProfile if a registered user is found without one.
        """
        if not student_id:
            return None

        profile = None
        skill_lookup = MLDataService._build_skill_lookup(db)

        # -------------------------------------------------------------
        # 1. Handle in-memory MockDatabaseSession
        # -------------------------------------------------------------
        if MLDataService._is_mock(db):
            # STU_00X demo convention
            if isinstance(student_id, str) and student_id.upper().startswith("STU_"):
                try:
                    idx = int(student_id.split("_")[1])
                    user_id = 1000 + idx
                    profile = next((p for p in db.student_profiles.values() if p.user_id == user_id or p.id == idx), None)
                except (IndexError, ValueError):
                    pass

            if not profile:
                try:
                    num_id = int(student_id)
                    profile = next((p for p in db.student_profiles.values() if p.user_id == num_id or p.id == num_id), None)
                    if not profile:
                        user = getattr(db, "users", {}).get(num_id)
                        if not user:
                            try:
                                from app.services.auth_service import AuthService
                                from app.db.database import SessionLocal
                                with SessionLocal() as s:
                                    db_u = AuthService.get_user_by_id(s, num_id)
                                    if db_u:
                                        from app.models.users import User as EntityUser
                                        user = EntityUser(id=db_u.id, email=db_u.email, role=db_u.role)
                                        db.users[db_u.id] = user
                            except Exception:
                                pass
                        if user:
                            new_id = len(db.student_profiles) + 1
                            profile = EntityStudentProfile(id=new_id, user_id=num_id, target_role_id="ROLE_FULL_STACK_DEV")
                            db.student_profiles[new_id] = profile
                except (ValueError, TypeError):
                    pass

            if not profile:
                return None

            evidence_list = [e for e in getattr(db, "student_skill_evidence", []) if e.student_profile_id == profile.id]
            evidence_dicts = [
                {
                    "skill_id": skill_lookup.get(e.skill_id, skill_lookup.get(str(e.skill_id), str(e.skill_id))),
                    "evidence_type": e.evidence_type,
                    "evidence_strength": e.strength,
                    "metadata": e.metadata if isinstance(getattr(e, "metadata", None), dict) else (getattr(e, "metadata_", {}) or {})
                }
                for e in evidence_list
            ]

            return {
                "student_id": str(student_id),
                "profile_id": profile.id,
                "user_id": profile.user_id,
                "target_role_id": profile.target_role_id,
                "evidence_records": evidence_dicts
            }

        # -------------------------------------------------------------
        # 2. Handle SQLAlchemy database session
        # -------------------------------------------------------------
        elif hasattr(db, "query"):
            from app.models.student_roles import (
                StudentProfile as DBStudentProfile,
                StudentSkillEvidence as DBStudentSkillEvidence
            )
            from app.models.users import User as DBUser

            # STU_00X demo convention
            if isinstance(student_id, str) and student_id.upper().startswith("STU_"):
                try:
                    idx = int(student_id.split("_")[1])
                    user_id = 1000 + idx
                    profile = db.query(DBStudentProfile).filter(
                        (DBStudentProfile.user_id == user_id) | (DBStudentProfile.id == idx)
                    ).first()
                except (IndexError, ValueError):
                    pass

            # Numeric user_id or profile_id
            if not profile:
                try:
                    num_id = int(student_id)
                    profile = db.query(DBStudentProfile).filter(
                        (DBStudentProfile.user_id == num_id) | (DBStudentProfile.id == num_id)
                    ).first()

                    # If not found, check if User exists and auto-create StudentProfile
                    if not profile:
                        user = db.query(DBUser).filter(DBUser.id == num_id).first()
                        if user:
                            profile = DBStudentProfile(
                                user_id=user.id,
                                target_role_id="ROLE_FULL_STACK_DEV"
                            )
                            db.add(profile)
                            db.commit()
                            db.refresh(profile)
                except (ValueError, TypeError):
                    pass

            if not profile:
                return None

            evidence_records = db.query(DBStudentSkillEvidence).filter(
                DBStudentSkillEvidence.student_profile_id == profile.id
            ).all()

            evidence_dicts = []
            for e in evidence_records:
                sk_id = None
                if hasattr(e, "skill") and e.skill and hasattr(e.skill, "skill_id"):
                    sk_id = e.skill.skill_id
                if not sk_id:
                    raw_sk = getattr(e, "skill_id", "")
                    sk_id = skill_lookup.get(raw_sk, skill_lookup.get(str(raw_sk), str(raw_sk) if raw_sk else ""))
                canonical = skill_lookup.get(sk_id, str(sk_id))
                meta = getattr(e, "metadata_", getattr(e, "metadata", {})) or {}
                evidence_dicts.append({
                    "skill_id": canonical,
                    "evidence_type": e.evidence_type,
                    "evidence_strength": e.strength,
                    "metadata": meta
                })

            return {
                "student_id": str(student_id),
                "profile_id": profile.id,
                "user_id": profile.user_id,
                "target_role_id": profile.target_role_id,
                "evidence_records": evidence_dicts
            }

        return None
