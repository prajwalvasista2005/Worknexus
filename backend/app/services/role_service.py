from typing import List, Optional, Any
from app.models.student_roles import (
    TargetRole as EntityTargetRole,
    RoleSkill as EntityRoleSkill
)
from app.models.skills import Skill as EntitySkill
from ..schemas.schemas import TargetRoleCreateSchema, TargetRoleResponseSchema

class RoleService:
    """
    Unified service for Target Roles and Role Skills.
    Supports both SQLAlchemy relational database sessions and lightweight MockDatabaseSession.
    """

    @staticmethod
    def _is_mock(db: Any) -> bool:
        return hasattr(db, "target_roles") or hasattr(db, "users")

    @staticmethod
    def create_role(db: Any, role_in: TargetRoleCreateSchema) -> TargetRoleResponseSchema:
        # -------------------------------------------------------------
        # 1. In-memory MockDatabaseSession branch
        # -------------------------------------------------------------
        if RoleService._is_mock(db):
            for sk_id in role_in.skill_ids:
                if sk_id not in getattr(db, "skills", {}):
                    raise ValueError(f"Skill '{sk_id}' not found in canonical taxonomy.")

            role = EntityTargetRole(
                id=role_in.id,
                name=role_in.name,
                description=role_in.description,
                is_active=True
            )
            db.add(role)

            for sk_id in role_in.skill_ids:
                new_id = len(db.role_skills) + 1
                rs = EntityRoleSkill(id=new_id, role_id=role_in.id, skill_id=sk_id)
                db.add(rs)

            db.commit()

            return TargetRoleResponseSchema(
                id=role.id,
                name=role.name,
                description=role.description,
                is_active=role.is_active,
                required_skills=role_in.skill_ids,
                created_at=role.created_at
            )

        # -------------------------------------------------------------
        # 2. SQLAlchemy database session branch
        # -------------------------------------------------------------
        from app.models.student_roles import TargetRole as DBTargetRole, RoleSkill as DBRoleSkill
        from app.models.skills import Skill as DBSkill

        resolved_skill_records = []
        for sk_id in role_in.skill_ids:
            skill = db.query(DBSkill).filter(DBSkill.skill_id == sk_id).first()
            if not skill and sk_id.isdigit():
                skill = db.query(DBSkill).filter(DBSkill.id == int(sk_id)).first()
            if not skill:
                raise ValueError(f"Skill '{sk_id}' not found in canonical taxonomy.")
            resolved_skill_records.append(skill)

        role = db.query(DBTargetRole).filter(DBTargetRole.id == role_in.id).first()
        if not role:
            role = DBTargetRole(
                id=role_in.id,
                name=role_in.name,
                description=role_in.description,
                is_active=True
            )
            db.add(role)
            db.commit()
            db.refresh(role)
        else:
            role.name = role_in.name
            role.description = role_in.description
            db.commit()
            db.refresh(role)

        # Sync role skills
        existing_skills = {rs.skill_id for rs in db.query(DBRoleSkill).filter(DBRoleSkill.role_id == role.id).all()}
        for sk in resolved_skill_records:
            if sk.id not in existing_skills:
                rs = DBRoleSkill(role_id=role.id, skill_id=sk.id)
                db.add(rs)
        db.commit()

        return TargetRoleResponseSchema(
            id=role.id,
            name=role.name,
            description=role.description,
            is_active=role.is_active,
            required_skills=role_in.skill_ids,
            created_at=role.created_at
        )

    @staticmethod
    def get_role(db: Any, role_id: str) -> Optional[TargetRoleResponseSchema]:
        # -------------------------------------------------------------
        # 1. In-memory MockDatabaseSession branch
        # -------------------------------------------------------------
        if RoleService._is_mock(db):
            role = db.target_roles.get(role_id)
            if not role:
                return None

            skills = [rs.skill_id for rs in getattr(db, "role_skills", []) if rs.role_id == role_id]
            return TargetRoleResponseSchema(
                id=role.id,
                name=role.name,
                description=role.description,
                is_active=role.is_active,
                required_skills=sorted(skills),
                created_at=role.created_at
            )

        # -------------------------------------------------------------
        # 2. SQLAlchemy database session branch
        # -------------------------------------------------------------
        from app.models.student_roles import TargetRole as DBTargetRole, RoleSkill as DBRoleSkill

        role = db.query(DBTargetRole).filter(DBTargetRole.id == role_id).first()
        if not role:
            return None

        role_skills = db.query(DBRoleSkill).filter(DBRoleSkill.role_id == role_id).all()
        skills = []
        for rs in role_skills:
            if hasattr(rs, "skill") and rs.skill and hasattr(rs.skill, "skill_id"):
                skills.append(rs.skill.skill_id)
            else:
                skills.append(str(rs.skill_id))

        return TargetRoleResponseSchema(
            id=role.id,
            name=role.name,
            description=role.description,
            is_active=role.is_active,
            required_skills=sorted(skills),
            created_at=role.created_at
        )

    @staticmethod
    def list_roles(db: Any) -> List[TargetRoleResponseSchema]:
        # -------------------------------------------------------------
        # 1. In-memory MockDatabaseSession branch
        # -------------------------------------------------------------
        if RoleService._is_mock(db):
            roles = list(getattr(db, "target_roles", {}).values())
            results = []
            for r in roles:
                skills = [rs.skill_id for rs in getattr(db, "role_skills", []) if rs.role_id == r.id]
                results.append(TargetRoleResponseSchema(
                    id=r.id,
                    name=r.name,
                    description=r.description,
                    is_active=r.is_active,
                    required_skills=sorted(skills),
                    created_at=r.created_at
                ))
            return sorted(results, key=lambda x: x.id)

        # -------------------------------------------------------------
        # 2. SQLAlchemy database session branch
        # -------------------------------------------------------------
        from app.models.student_roles import TargetRole as DBTargetRole, RoleSkill as DBRoleSkill

        roles = db.query(DBTargetRole).all()
        all_role_skills = db.query(DBRoleSkill).all()

        skills_by_role = {}
        for rs in all_role_skills:
            sk_id = rs.skill.skill_id if (hasattr(rs, "skill") and rs.skill and hasattr(rs.skill, "skill_id")) else str(rs.skill_id)
            skills_by_role.setdefault(rs.role_id, []).append(sk_id)

        results = []
        for r in roles:
            results.append(TargetRoleResponseSchema(
                id=r.id,
                name=r.name,
                description=r.description,
                is_active=r.is_active,
                required_skills=sorted(skills_by_role.get(r.id, [])),
                created_at=r.created_at
            ))

        return sorted(results, key=lambda x: x.id)
