from typing import List, Optional, Any, Dict
from app.models.student_roles import (
    StudentProfile as EntityStudentProfile,
    StudentSkillEvidence as EntityStudentSkillEvidence,
    TargetRole as EntityTargetRole
)
from app.models.users import User as EntityUser
from app.models.skills import Skill as EntitySkill
from ..schemas.schemas import (
    StudentProfileCreateSchema,
    StudentProfileResponseSchema,
    StudentSkillEvidenceCreateSchema,
    StudentSkillEvidenceResponseSchema
)

class StudentService:
    """
    Unified service for Student Profiles and Skill Evidence.
    Supports both SQLAlchemy relational database sessions and lightweight MockDatabaseSession.
    """

    @staticmethod
    def _is_mock(db: Any) -> bool:
        return hasattr(db, "student_profiles") or hasattr(db, "users")

    @staticmethod
    def create_or_get_profile(db: Any, profile_in: StudentProfileCreateSchema) -> StudentProfileResponseSchema:
        # -------------------------------------------------------------
        # 1. In-memory MockDatabaseSession branch
        # -------------------------------------------------------------
        if StudentService._is_mock(db):
            user = db.users.get(profile_in.user_id)
            if not user:
                try:
                    from app.services.auth_service import AuthService
                    from app.db.database import SessionLocal
                    with SessionLocal() as s:
                        db_u = AuthService.get_user_by_id(s, profile_in.user_id)
                        if db_u:
                            from app.models.users import User as EntityUser
                            user = EntityUser(id=db_u.id, email=db_u.email, role=db_u.role)
                            db.users[db_u.id] = user
                except Exception:
                    pass

            if not user:
                raise ValueError(f"User with ID {profile_in.user_id} does not exist.")

            profile = next((p for p in db.student_profiles.values() if p.user_id == profile_in.user_id), None)

            if profile_in.target_role_id:
                if profile_in.target_role_id not in getattr(db, "target_roles", {}):
                    raise ValueError(f"TargetRole '{profile_in.target_role_id}' does not exist.")

            if not profile:
                new_id = len(db.student_profiles) + 1
                profile = EntityStudentProfile(
                    id=new_id,
                    user_id=profile_in.user_id,
                    target_role_id=profile_in.target_role_id or "ROLE_FULL_STACK_DEV"
                )
                db.add(profile)
                db.commit()
            else:
                if profile_in.target_role_id:
                    profile.target_role_id = profile_in.target_role_id
                    db.commit()

            evidence_records = StudentService.get_student_evidence(db, profile.user_id)
            return StudentProfileResponseSchema(
                id=profile.id,
                user_id=profile.user_id,
                target_role_id=profile.target_role_id,
                evidence_records=evidence_records,
                created_at=profile.created_at
            )

        # -------------------------------------------------------------
        # 2. SQLAlchemy database session branch
        # -------------------------------------------------------------
        from app.models.users import User as DBUser
        from app.models.student_roles import (
            StudentProfile as DBStudentProfile,
            TargetRole as DBTargetRole
        )

        user = db.query(DBUser).filter(DBUser.id == profile_in.user_id).first()
        if not user:
            raise ValueError(f"User with ID {profile_in.user_id} does not exist.")

        if profile_in.target_role_id:
            role = db.query(DBTargetRole).filter(DBTargetRole.id == profile_in.target_role_id).first()
            if not role:
                raise ValueError(f"TargetRole '{profile_in.target_role_id}' does not exist.")

        profile = db.query(DBStudentProfile).filter(DBStudentProfile.user_id == profile_in.user_id).first()
        if not profile:
            profile = DBStudentProfile(
                user_id=profile_in.user_id,
                target_role_id=profile_in.target_role_id or "ROLE_FULL_STACK_DEV"
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)
        else:
            if profile_in.target_role_id:
                profile.target_role_id = profile_in.target_role_id
                db.commit()
                db.refresh(profile)

        evidence_records = StudentService.get_student_evidence(db, profile.user_id)
        return StudentProfileResponseSchema(
            id=profile.id,
            user_id=profile.user_id,
            target_role_id=profile.target_role_id,
            evidence_records=evidence_records,
            created_at=profile.created_at
        )

    @staticmethod
    def get_profile_by_user_id(db: Any, user_id: int) -> Optional[StudentProfileResponseSchema]:
        # -------------------------------------------------------------
        # 1. In-memory MockDatabaseSession branch
        # -------------------------------------------------------------
        if StudentService._is_mock(db):
            profile = next((p for p in db.student_profiles.values() if p.user_id == user_id), None)
            if not profile:
                user = getattr(db, "users", {}).get(user_id)
                if not user:
                    try:
                        from app.services.auth_service import AuthService
                        from app.db.database import SessionLocal
                        with SessionLocal() as s:
                            db_u = AuthService.get_user_by_id(s, user_id)
                            if db_u:
                                from app.models.users import User as EntityUser
                                user = EntityUser(id=db_u.id, email=db_u.email, role=db_u.role)
                                db.users[db_u.id] = user
                    except Exception:
                        pass

                if user:
                    new_id = len(db.student_profiles) + 1
                    profile = EntityStudentProfile(
                        id=new_id,
                        user_id=user_id,
                        target_role_id="ROLE_FULL_STACK_DEV"
                    )
                    db.add(profile)
                    db.commit()

            if not profile:
                return None

            evidence_records = StudentService.get_student_evidence(db, user_id)
            return StudentProfileResponseSchema(
                id=profile.id,
                user_id=profile.user_id,
                target_role_id=profile.target_role_id,
                evidence_records=evidence_records,
                created_at=profile.created_at
            )

        # -------------------------------------------------------------
        # 2. SQLAlchemy database session branch
        # -------------------------------------------------------------
        from app.models.users import User as DBUser
        from app.models.student_roles import StudentProfile as DBStudentProfile

        profile = db.query(DBStudentProfile).filter(DBStudentProfile.user_id == user_id).first()
        if not profile:
            user = db.query(DBUser).filter(DBUser.id == user_id).first()
            if user:
                # Auto-create profile for registered user so student endpoints work immediately
                profile = DBStudentProfile(
                    user_id=user.id,
                    target_role_id="ROLE_FULL_STACK_DEV"
                )
                db.add(profile)
                db.commit()
                db.refresh(profile)

        if not profile:
            return None

        evidence_records = StudentService.get_student_evidence(db, user_id)
        return StudentProfileResponseSchema(
            id=profile.id,
            user_id=profile.user_id,
            target_role_id=profile.target_role_id,
            evidence_records=evidence_records,
            created_at=profile.created_at
        )

    @staticmethod
    def add_skill_evidence(
        db: Any,
        user_id: int,
        evidence_in: StudentSkillEvidenceCreateSchema
    ) -> StudentSkillEvidenceResponseSchema:
        VALID_EVIDENCE_TYPES = {
            "self_reported",
            "course_completed",
            "project",
            "certification",
            "assessment"
        }
        VALID_STRENGTH_CATEGORIES = {
            "basic",
            "intermediate",
            "advanced"
        }
        if evidence_in.evidence_type not in VALID_EVIDENCE_TYPES:
            raise ValueError(f"Invalid evidence_type '{evidence_in.evidence_type}'. Must be one of: {sorted(list(VALID_EVIDENCE_TYPES))}")
        if evidence_in.strength not in VALID_STRENGTH_CATEGORIES:
            raise ValueError(f"Invalid strength category '{evidence_in.strength}'. Must be one of: {sorted(list(VALID_STRENGTH_CATEGORIES))}")

        # -------------------------------------------------------------
        # 1. In-memory MockDatabaseSession branch
        # -------------------------------------------------------------
        if StudentService._is_mock(db):
            profile = next((p for p in db.student_profiles.values() if p.user_id == user_id), None)
            if not profile:
                profile_res = StudentService.create_or_get_profile(db, StudentProfileCreateSchema(user_id=user_id))
                profile = db.student_profiles[profile_res.id]

            raw_inp = str(evidence_in.skill_id).strip()
            target_skill = None
            try:
                from app.services.skill_service import SkillService
                target_skill = SkillService.get_or_create_skill(db, raw_inp)
            except Exception:
                target_skill = None

            if not target_skill:
                alt_prefix = "SK_" + raw_inp[6:] if raw_inp.upper().startswith("SKILL_") else None
                for s in getattr(db, "skills", {}).values():
                    scode = getattr(s, "skill_id", getattr(s, "id", None))
                    sname = getattr(s, "name", "")
                    sid = getattr(s, "id", None)
                    cand_ids = [str(scode).lower(), str(sname).lower(), str(sid).lower()]
                    if raw_inp.lower() in cand_ids or (alt_prefix and alt_prefix.lower() in cand_ids):
                        target_skill = s
                        break

                if not target_skill and raw_inp in getattr(db, "skills", {}):
                    target_skill = db.skills[raw_inp]
                if not target_skill and alt_prefix and alt_prefix in getattr(db, "skills", {}):
                    target_skill = db.skills[alt_prefix]

            if not target_skill:
                raise ValueError(f"Skill '{evidence_in.skill_id}' not found in canonical taxonomy.")

            canonical_skill_id = getattr(target_skill, "skill_id", getattr(target_skill, "id", raw_inp))

            new_id = len(db.student_skill_evidence) + 1
            evidence = EntityStudentSkillEvidence(
                id=new_id,
                student_profile_id=profile.id,
                skill_id=canonical_skill_id,
                evidence_type=evidence_in.evidence_type,
                strength=evidence_in.strength,
                metadata=evidence_in.metadata
            )
            db.add(evidence)
            db.commit()

            # 1. Automatic Profile Skill Upsert
            strength_val = str(evidence_in.strength or "advanced").strip().lower()
            if "basic" in strength_val or "beginner" in strength_val or "low" in strength_val:
                prof_level = "Basic"
            elif "intermediate" in strength_val or "medium" in strength_val:
                prof_level = "Intermediate"
            else:
                prof_level = "Advanced"

            if not hasattr(db, "user_skills"):
                db.user_skills = []
            if not hasattr(db, "student_skills"):
                db.student_skills = db.user_skills

            target_id = getattr(target_skill, "id", None)
            existing_us = None
            for us in getattr(db, "user_skills", []):
                if getattr(us, "user_id", None) == user_id:
                    us_sk = getattr(us, "skill_id", None)
                    if us_sk in (target_id, canonical_skill_id, str(target_id), str(canonical_skill_id)):
                        existing_us = us
                        break

            if not existing_us:
                from app.models.user_skills import UserSkill
                new_us = UserSkill(
                    user_id=user_id,
                    skill_id=target_id or canonical_skill_id,
                    proficiency_level=prof_level,
                    source="Verified Evidence"
                )
                db.add(new_us)
                db.commit()
            else:
                level_order = {"basic": 1, "intermediate": 2, "advanced": 3}
                cur_rank = level_order.get(str(getattr(existing_us, "proficiency_level", "")).lower(), 1)
                new_rank = level_order.get(prof_level.lower(), 3)
                if new_rank > cur_rank:
                    existing_us.proficiency_level = prof_level
                existing_us.source = "Verified Evidence"
                db.commit()

            # 2. Cascading Gap Recalculation
            gap_data = StudentService.recalculate_student_gap(db, user_id, profile.target_role_id)

            meta = evidence.metadata if isinstance(getattr(evidence, "metadata", None), dict) else (getattr(evidence, "metadata_", {}) or {})
            return StudentSkillEvidenceResponseSchema(
                id=evidence.id,
                student_profile_id=evidence.student_profile_id,
                skill_id=canonical_skill_id,
                evidence_type=evidence.evidence_type,
                strength=evidence.strength,
                metadata=meta,
                created_at=evidence.created_at,
                match_score=gap_data.get("match_score"),
                overall_match_score=gap_data.get("overall_match_score"),
                gap_percentage=gap_data.get("gap_percentage"),
                gap_score=gap_data.get("gap_score"),
                acquired_skills=gap_data.get("acquired_skills", []),
                skills_acquired=gap_data.get("skills_acquired", []),
                missing_skills=gap_data.get("missing_skills", []),
                skills_missing=gap_data.get("skills_missing", []),
                recalculated_gap=gap_data,
                gap_analysis=gap_data
            )

        # -------------------------------------------------------------
        # 2. SQLAlchemy database session branch
        # -------------------------------------------------------------
        from sqlalchemy import func
        from app.models.skills import Skill as DBSkill
        from app.models.student_roles import (
            StudentProfile as DBStudentProfile,
            StudentSkillEvidence as DBStudentSkillEvidence
        )
        from app.models.user_skills import UserSkill as DBUserSkill

        profile = db.query(DBStudentProfile).filter(DBStudentProfile.user_id == user_id).first()
        if not profile:
            StudentService.create_or_get_profile(db, StudentProfileCreateSchema(user_id=user_id))
            profile = db.query(DBStudentProfile).filter(DBStudentProfile.user_id == user_id).first()

        # Lookup skill in database (resolving canonical taxonomy, code, or name via SkillService)
        raw_inp = str(evidence_in.skill_id).strip()
        db_skill = None
        try:
            from app.services.skill_service import SkillService
            db_skill = SkillService.get_or_create_skill(db, raw_inp)
        except Exception:
            db_skill = None

        if not db_skill:
            alt_prefix = "SK_" + raw_inp[6:] if raw_inp.upper().startswith("SKILL_") else None
            db_skill = db.query(DBSkill).filter(DBSkill.skill_id == raw_inp).first()
            if not db_skill:
                db_skill = db.query(DBSkill).filter(func.lower(DBSkill.skill_id) == raw_inp.lower()).first()
            if not db_skill and alt_prefix:
                db_skill = db.query(DBSkill).filter(func.lower(DBSkill.skill_id) == alt_prefix.lower()).first()
            if not db_skill and raw_inp.isdigit():
                db_skill = db.query(DBSkill).filter(DBSkill.id == int(raw_inp)).first()
            if not db_skill:
                db_skill = db.query(DBSkill).filter(func.lower(DBSkill.name) == raw_inp.lower()).first()
            if not db_skill:
                db_skill = db.query(DBSkill).filter(DBSkill.name.ilike(f"%{raw_inp}%")).first()

        if not db_skill:
            raise ValueError(f"Skill '{evidence_in.skill_id}' not found in canonical taxonomy.")

        evidence = DBStudentSkillEvidence(
            student_profile_id=profile.id,
            skill_id=db_skill.id,
            evidence_type=evidence_in.evidence_type,
            strength=evidence_in.strength,
            metadata_=evidence_in.metadata
        )
        db.add(evidence)
        db.commit()
        db.refresh(evidence)

        # 1. Automatic Profile Skill Upsert
        strength_val = str(evidence_in.strength or "advanced").strip().lower()
        if "basic" in strength_val or "beginner" in strength_val or "low" in strength_val:
            prof_level = "Basic"
        elif "intermediate" in strength_val or "medium" in strength_val:
            prof_level = "Intermediate"
        else:
            prof_level = "Advanced"

        existing_user_skill = db.query(DBUserSkill).filter(
            DBUserSkill.user_id == user_id,
            DBUserSkill.skill_id == db_skill.id
        ).first()

        if not existing_user_skill:
            new_user_skill = DBUserSkill(
                user_id=user_id,
                skill_id=db_skill.id,
                proficiency_level=prof_level,
                source="Verified Evidence"
            )
            db.add(new_user_skill)
            db.commit()
            db.refresh(new_user_skill)
        else:
            level_order = {"basic": 1, "intermediate": 2, "advanced": 3}
            cur_rank = level_order.get(str(existing_user_skill.proficiency_level).lower(), 1)
            new_rank = level_order.get(prof_level.lower(), 3)
            if new_rank > cur_rank:
                existing_user_skill.proficiency_level = prof_level
            existing_user_skill.source = "Verified Evidence"
            db.commit()

        # 2. Cascading Gap Recalculation
        gap_data = StudentService.recalculate_student_gap(db, user_id, profile.target_role_id)

        return StudentSkillEvidenceResponseSchema(
            id=evidence.id,
            student_profile_id=evidence.student_profile_id,
            skill_id=db_skill.skill_id,
            evidence_type=evidence.evidence_type,
            strength=evidence.strength,
            metadata=evidence.metadata_ or {},
            created_at=evidence.created_at,
            match_score=gap_data.get("match_score"),
            overall_match_score=gap_data.get("overall_match_score"),
            gap_percentage=gap_data.get("gap_percentage"),
            gap_score=gap_data.get("gap_score"),
            acquired_skills=gap_data.get("acquired_skills", []),
            skills_acquired=gap_data.get("skills_acquired", []),
            missing_skills=gap_data.get("missing_skills", []),
            skills_missing=gap_data.get("skills_missing", []),
            recalculated_gap=gap_data,
            gap_analysis=gap_data
        )

    @staticmethod
    def recalculate_student_gap(
        db: Any,
        user_id: int,
        target_role_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recalculates the student's role gap and match metrics after skill evidence is submitted.
        Returns a dictionary containing:
            - overall_match_score / match_score
            - gap_percentage / gap_score
            - acquired_skills / skills_acquired
            - missing_skills / skills_missing
            - total_role_skills
            - present_skills_count
            - missing_skills_count
        """
        if not target_role_id:
            profile = StudentService.get_profile_by_user_id(db, user_id)
            if profile and profile.target_role_id:
                target_role_id = profile.target_role_id
            else:
                target_role_id = "ROLE_FULL_STACK_DEV"

        try:
            from app.services.ml_adapter import MLAdapter
            adapter = MLAdapter()
            res = adapter.get_student_skill_gap(
                student_id=str(user_id),
                role_id=target_role_id,
                db=db,
                mode="live"
            )
            raw = res.to_dict() if hasattr(res, "to_dict") else dict(res)

            summary = raw.get("summary", {})
            skill_gaps = raw.get("skill_gaps", [])
            acquired = []
            missing_list = []
            for sg in skill_gaps:
                is_acquired = (
                    sg.get("student_status") == "present"
                    or sg.get("status") == "present"
                    or bool(sg.get("student_has_skill"))
                )
                sk_id = sg.get("skill_id", "")
                sk_name = sg.get("skill_name", sk_id)
                if is_acquired:
                    acquired.append({
                        "id": sk_id,
                        "skill_id": sk_id,
                        "name": sk_name,
                        "score": 1.0,
                        "strength": sg.get("strength") or sg.get("evidence_strength") or "intermediate",
                        "level": sg.get("level") or "intermediate"
                    })
                else:
                    missing_list.append({
                        "id": sk_id,
                        "skill_id": sk_id,
                        "name": sk_name,
                        "importance": 1.0,
                        "priority": "High"
                    })

            total = len(skill_gaps) if skill_gaps else (summary.get("total_role_skills", 1) or 1)
            present = len(acquired)
            missing = len(missing_list)
            match_score = round(present / total, 2) if total > 0 else 0.0
            gap_pct = round((missing / total) * 100.0, 1) if total > 0 else 0.0

            return {
                "role_id": target_role_id,
                "overall_match_score": match_score,
                "match_score": match_score,
                "gap_percentage": gap_pct,
                "gap_score": gap_pct,
                "acquired_skills": acquired,
                "skills_acquired": acquired,
                "missing_skills": missing_list,
                "skills_missing": missing_list,
                "total_role_skills": total,
                "present_skills_count": present,
                "missing_skills_count": missing,
            }
        except Exception:
            return {
                "role_id": target_role_id,
                "overall_match_score": 0.0,
                "match_score": 0.0,
                "gap_percentage": 100.0,
                "gap_score": 100.0,
                "acquired_skills": [],
                "skills_acquired": [],
                "missing_skills": [],
                "skills_missing": [],
                "total_role_skills": 0,
                "present_skills_count": 0,
                "missing_skills_count": 0,
            }

    @staticmethod
    def get_student_evidence(db: Any, user_id: int) -> List[StudentSkillEvidenceResponseSchema]:
        # Build lookup table id -> canonical skill_id
        skill_id_to_code = {}
        if StudentService._is_mock(db):
            for s in getattr(db, "skills", {}).values():
                sid = getattr(s, "id", None)
                scode = getattr(s, "skill_id", getattr(s, "id", None))
                if scode:
                    skill_id_to_code[str(scode)] = str(scode)
                    if sid is not None:
                        skill_id_to_code[sid] = str(scode)
                        skill_id_to_code[str(sid)] = str(scode)
        elif hasattr(db, "query"):
            try:
                from app.models.skills import Skill as DBSkill
                for s in db.query(DBSkill).all():
                    skill_id_to_code[s.id] = s.skill_id
                    skill_id_to_code[str(s.id)] = s.skill_id
                    skill_id_to_code[s.skill_id] = s.skill_id
            except Exception:
                pass

        # -------------------------------------------------------------
        # 1. In-memory MockDatabaseSession branch
        # -------------------------------------------------------------
        if StudentService._is_mock(db):
            profile = next((p for p in db.student_profiles.values() if p.user_id == user_id), None)
            if not profile:
                return []

            evidence_list = [e for e in getattr(db, "student_skill_evidence", []) if e.student_profile_id == profile.id]
            return [
                StudentSkillEvidenceResponseSchema(
                    id=e.id,
                    student_profile_id=e.student_profile_id,
                    skill_id=skill_id_to_code.get(e.skill_id, skill_id_to_code.get(str(e.skill_id), str(e.skill_id))),
                    evidence_type=e.evidence_type,
                    strength=e.strength,
                    metadata=e.metadata if isinstance(getattr(e, "metadata", None), dict) else (getattr(e, "metadata_", {}) or {}),
                    created_at=e.created_at
                )
                for e in evidence_list
            ]

        # -------------------------------------------------------------
        # 2. SQLAlchemy database session branch
        # -------------------------------------------------------------
        from app.models.student_roles import (
            StudentProfile as DBStudentProfile,
            StudentSkillEvidence as DBStudentSkillEvidence
        )

        profile = db.query(DBStudentProfile).filter(DBStudentProfile.user_id == user_id).first()
        if not profile:
            return []

        evidence_list = db.query(DBStudentSkillEvidence).filter(
            DBStudentSkillEvidence.student_profile_id == profile.id
        ).all()

        results = []
        for e in evidence_list:
            sk_id = None
            if hasattr(e, "skill") and e.skill and hasattr(e.skill, "skill_id"):
                sk_id = e.skill.skill_id
            if not sk_id:
                raw_sk = getattr(e, "skill_id", "")
                sk_id = skill_id_to_code.get(raw_sk, skill_id_to_code.get(str(raw_sk), str(raw_sk) if raw_sk else ""))
            canonical = skill_id_to_code.get(sk_id, str(sk_id))
            meta = getattr(e, "metadata_", getattr(e, "metadata", {})) or {}
            if isinstance(meta, str):
                try:
                    import json
                    meta = json.loads(meta)
                except Exception:
                    meta = {}
            results.append(StudentSkillEvidenceResponseSchema(
                id=e.id,
                student_profile_id=e.student_profile_id,
                skill_id=canonical,
                evidence_type=e.evidence_type,
                strength=e.strength,
                metadata=meta,
                created_at=e.created_at
            ))

        return results
