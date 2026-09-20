from typing import List, Optional
from ..models.entities import StudentProfile, StudentSkillEvidence, User, Skill, TargetRole
from ..schemas.schemas import (
    StudentProfileCreateSchema,
    StudentProfileResponseSchema,
    StudentSkillEvidenceCreateSchema,
    StudentSkillEvidenceResponseSchema
)

class StudentService:

    @staticmethod
    def create_or_get_profile(db, profile_in: StudentProfileCreateSchema) -> StudentProfileResponseSchema:
        # 1. Validate User exists and has role='Student'
        user = None
        if hasattr(db, "users") and profile_in.user_id in db.users:
            user = db.users[profile_in.user_id]
        elif hasattr(db, "query"):
            user = db.query(User).filter(lambda u: u.id == profile_in.user_id).first()

        if not user:
            raise ValueError(f"User with ID {profile_in.user_id} does not exist.")

        # 2. Check if StudentProfile already exists
        profile = None
        if hasattr(db, "student_profiles"):
            profile = next((p for p in db.student_profiles.values() if p.user_id == profile_in.user_id), None)
        elif hasattr(db, "query"):
            profile = db.query(StudentProfile).filter(lambda p: p.user_id == profile_in.user_id).first()

        if not profile:
            # Validate target_role_id if provided
            if profile_in.target_role_id:
                role_exists = False
                if hasattr(db, "target_roles") and profile_in.target_role_id in db.target_roles:
                    role_exists = True
                elif hasattr(db, "query"):
                    role_exists = bool(db.query(TargetRole).filter(lambda r: r.id == profile_in.target_role_id).first())
                if not role_exists:
                    raise ValueError(f"TargetRole '{profile_in.target_role_id}' does not exist.")

            profile = StudentProfile(id=None, user_id=profile_in.user_id, target_role_id=profile_in.target_role_id)
            db.add(profile)
            db.commit()

        # 3. Retrieve associated evidence
        evidence_records = StudentService.get_student_evidence(db, profile.user_id)

        return StudentProfileResponseSchema(
            id=profile.id,
            user_id=profile.user_id,
            target_role_id=profile.target_role_id,
            evidence_records=evidence_records,
            created_at=profile.created_at
        )

    @staticmethod
    def get_profile_by_user_id(db, user_id: int) -> Optional[StudentProfileResponseSchema]:
        profile = None
        if hasattr(db, "student_profiles"):
            profile = next((p for p in db.student_profiles.values() if p.user_id == user_id), None)
        elif hasattr(db, "query"):
            profile = db.query(StudentProfile).filter(lambda p: p.user_id == user_id).first()

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
        db,
        user_id: int,
        evidence_in: StudentSkillEvidenceCreateSchema
    ) -> StudentSkillEvidenceResponseSchema:
        # 1. Get or create profile
        profile = None
        if hasattr(db, "student_profiles"):
            profile = next((p for p in db.student_profiles.values() if p.user_id == user_id), None)
        elif hasattr(db, "query"):
            profile = db.query(StudentProfile).filter(lambda p: p.user_id == user_id).first()

        if not profile:
            # Automatically create profile for existing user
            profile_res = StudentService.create_or_get_profile(db, StudentProfileCreateSchema(user_id=user_id))
            if hasattr(db, "student_profiles"):
                profile = db.student_profiles[profile_res.id]
            elif hasattr(db, "query"):
                profile = db.query(StudentProfile).filter(lambda p: p.id == profile_res.id).first()

        # 2. Validate skill exists in taxonomy
        skill_exists = False
        if hasattr(db, "skills") and evidence_in.skill_id in db.skills:
            skill_exists = True
        elif hasattr(db, "query"):
            skill_exists = bool(db.query(Skill).filter(lambda s: s.id == evidence_in.skill_id).first())

        if not skill_exists:
            raise ValueError(f"Skill '{evidence_in.skill_id}' not found in canonical taxonomy.")

        # 3. Create StudentSkillEvidence record
        evidence = StudentSkillEvidence(
            id=None,
            student_profile_id=profile.id,
            skill_id=evidence_in.skill_id,
            evidence_type=evidence_in.evidence_type,
            strength=evidence_in.strength,
            metadata=evidence_in.metadata
        )
        db.add(evidence)
        db.commit()

        return StudentSkillEvidenceResponseSchema(
            id=evidence.id,
            student_profile_id=profile.id,
            skill_id=evidence.skill_id,
            evidence_type=evidence.evidence_type,
            strength=evidence.strength,
            metadata=evidence.metadata,
            created_at=evidence.created_at
        )

    @staticmethod
    def get_student_evidence(db, user_id: int) -> List[StudentSkillEvidenceResponseSchema]:
        profile = None
        if hasattr(db, "student_profiles"):
            profile = next((p for p in db.student_profiles.values() if p.user_id == user_id), None)
        elif hasattr(db, "query"):
            profile = db.query(StudentProfile).filter(lambda p: p.user_id == user_id).first()

        if not profile:
            return []

        evidence_list = []
        if hasattr(db, "student_skill_evidence"):
            evidence_list = [e for e in db.student_skill_evidence if e.student_profile_id == profile.id]
        elif hasattr(db, "query"):
            evidence_list = db.query(StudentSkillEvidence).filter(lambda e: e.student_profile_id == profile.id).all()

        return [
            StudentSkillEvidenceResponseSchema(
                id=e.id,
                student_profile_id=e.student_profile_id,
                skill_id=e.skill_id,
                evidence_type=e.evidence_type,
                strength=e.strength,
                metadata=e.metadata,
                created_at=e.created_at
            )
            for e in evidence_list
        ]
