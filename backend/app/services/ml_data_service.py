from typing import Dict, List, Any, Tuple, Optional, Union
from collections import defaultdict
from ..models.entities import (
    JobPosting, JobSkill, Course, CourseSkill, Employer, EmployerFeedback, EmployerFeedbackSignal,
    TargetRole, RoleSkill, StudentProfile, StudentSkillEvidence
)

class MLDataService:
    """
    Backend service responsible for preparing live database records into
    pure domain dictionaries for the MLAdapter without N+1 queries.
    """

    @staticmethod
    def get_live_jobs_data(db) -> Tuple[List[Dict[str, Any]], int]:
        """
        Fetch all job postings and their associated skill extractions.
        """
        if hasattr(db, "job_postings"):
            all_jobs = list(db.job_postings.values())
            all_skills = list(db.job_skills)
        elif hasattr(db, "query"):
            all_jobs = db.query(JobPosting).all()
            all_skills = db.query(JobSkill).all()
        else:
            all_jobs = []
            all_skills = []

        total_jobs_count = len(all_jobs)
        skills_by_job: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for s in all_skills:
            skills_by_job[s.job_id].append({
                "skill_id": s.skill_id,
                "confidence_score": s.confidence_score
            })

        jobs_list = []
        for j in all_jobs:
            jobs_list.append({
                "job_id": str(j.id),
                "title": j.title,
                "company": j.company,
                "location": j.location,
                "source": "worknexus_db",
                "skills": skills_by_job.get(j.id, [])
            })

        return jobs_list, total_jobs_count

    @staticmethod
    def get_live_courses_data(db) -> List[Dict[str, Any]]:
        """
        Fetch all courses and their taught skills.
        """
        if hasattr(db, "courses"):
            all_courses = list(db.courses.values())
            all_course_skills = list(db.course_skills)
        elif hasattr(db, "query"):
            all_courses = db.query(Course).all()
            all_course_skills = db.query(CourseSkill).all()
        else:
            all_courses = []
            all_course_skills = []

        skills_by_course: Dict[int, List[str]] = defaultdict(list)
        for cs in all_course_skills:
            skills_by_course[cs.course_id].append(cs.skill_id)

        courses_list = []
        for c in all_courses:
            courses_list.append({
                "course_id": c.id,
                "course_name": c.name,
                "taught_skills": skills_by_course.get(c.id, [])
            })

        return courses_list

    @staticmethod
    def get_live_employer_feedback_data(db) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Fetch all employer feedback records and detected skill signals.
        """
        if hasattr(db, "employer_feedback"):
            all_fb = list(db.employer_feedback.values())
            all_signals = list(db.employer_feedback_signals)
            all_employers = db.employers
        elif hasattr(db, "query"):
            all_fb = db.query(EmployerFeedback).all()
            all_signals = db.query(EmployerFeedbackSignal).all()
            all_employers = {e.id: e for e in db.query(Employer).all()}
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
            sk_id = sig.skill_id
            fb = next((f for f in all_fb if f.id == sig.feedback_id), None)
            emp_id = fb.employer_id if fb else None
            
            signal_agg[sk_id]["feedback_count"] += 1
            if emp_id:
                signal_agg[sk_id]["employers"].add(emp_id)
            signal_agg[sk_id]["weighted_signal_sum"] += sig.weighted_signal

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
            emp = all_employers.get(f.employer_id)
            trust = getattr(emp, "trust_weight", 1.0) if emp else 1.0
            fb_list.append({
                "feedback_id": str(f.id),
                "employer_id": f.employer_id,
                "course_id": f.course_id,
                "trust_weight": trust,
                "comments": f.comments
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
        if hasattr(db, "target_roles") and role_id in db.target_roles:
            role = db.target_roles[role_id]
        elif hasattr(db, "query"):
            role = db.query(TargetRole).filter(lambda r: r.id == role_id).first()

        if not role:
            return None

        # Fetch role skills
        if hasattr(db, "role_skills"):
            skills = [rs.skill_id for rs in db.role_skills if rs.role_id == role.id]
        elif hasattr(db, "query"):
            skills = [rs.skill_id for rs in db.query(RoleSkill).filter(lambda rs: rs.role_id == role.id).all()]
        else:
            skills = []

        return {
            "role_id": role.id,
            "role_name": role.name,
            "description": role.description,
            "required_skills": sorted(skills)
        }

    @staticmethod
    def get_live_student_data(db, student_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        Fetch a student profile and all associated skill evidence records.
        Resolves integer user_id / profile_id, or demo 'STU_00X' string IDs.
        """
        if not student_id:
            return None

        profile = None

        # 1. If student_id is STU_00X, match by demo seed convention (user_id = 1000 + idx or profile.id = idx)
        if isinstance(student_id, str) and student_id.upper().startswith("STU_"):
            try:
                idx = int(student_id.split("_")[1])
                user_id = 1000 + idx
                if hasattr(db, "student_profiles"):
                    profile = next((p for p in db.student_profiles.values() if p.user_id == user_id or p.id == idx), None)
                elif hasattr(db, "query"):
                    profile = db.query(StudentProfile).filter(lambda p: p.user_id == user_id or p.id == idx).first()
            except (IndexError, ValueError):
                pass

        # 2. If student_id is int or string integer
        if not profile:
            try:
                numeric_id = int(student_id)
                if hasattr(db, "student_profiles"):
                    profile = next((p for p in db.student_profiles.values() if p.user_id == numeric_id or p.id == numeric_id), None)
                elif hasattr(db, "query"):
                    profile = db.query(StudentProfile).filter(lambda p: p.user_id == numeric_id or p.id == numeric_id).first()
            except (ValueError, TypeError):
                pass

        if not profile:
            return None

        # Retrieve evidence records
        evidence_list = []
        if hasattr(db, "student_skill_evidence"):
            evidence_list = [e for e in db.student_skill_evidence if e.student_profile_id == profile.id]
        elif hasattr(db, "query"):
            evidence_list = db.query(StudentSkillEvidence).filter(lambda e: e.student_profile_id == profile.id).all()

        evidence_dicts = [
            {
                "skill_id": e.skill_id,
                "evidence_type": e.evidence_type,
                "evidence_strength": e.strength,
                "metadata": e.metadata or {}
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
