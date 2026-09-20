from typing import List, Optional
from ..models.entities import TargetRole, RoleSkill, Skill
from ..schemas.schemas import TargetRoleCreateSchema, TargetRoleResponseSchema

class RoleService:

    @staticmethod
    def create_role(db, role_in: TargetRoleCreateSchema) -> TargetRoleResponseSchema:
        # 1. Validate skills exist
        for sk_id in role_in.skill_ids:
            skill = None
            if hasattr(db, "skills") and sk_id in db.skills:
                skill = db.skills[sk_id]
            elif hasattr(db, "query"):
                skill = db.query(Skill).filter(lambda s: s.id == sk_id).first()

            if not skill:
                raise ValueError(f"Skill '{sk_id}' not found in canonical taxonomy.")

        # 2. Create TargetRole entity
        role = TargetRole(
            id=role_in.id,
            name=role_in.name,
            description=role_in.description,
            is_active=True
        )
        db.add(role)

        # 3. Create RoleSkill associations
        for sk_id in role_in.skill_ids:
            rs = RoleSkill(id=None, role_id=role_in.id, skill_id=sk_id)
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
    def get_role(db, role_id: str) -> Optional[TargetRoleResponseSchema]:
        role = None
        if hasattr(db, "target_roles") and role_id in db.target_roles:
            role = db.target_roles[role_id]
        elif hasattr(db, "query"):
            role = db.query(TargetRole).filter(lambda r: r.id == role_id).first()

        if not role:
            return None

        # Fetch required skills
        skills = []
        if hasattr(db, "role_skills"):
            skills = [rs.skill_id for rs in db.role_skills if rs.role_id == role_id]
        elif hasattr(db, "query"):
            skills = [rs.skill_id for rs in db.query(RoleSkill).filter(lambda rs: rs.role_id == role_id).all()]

        return TargetRoleResponseSchema(
            id=role.id,
            name=role.name,
            description=role.description,
            is_active=role.is_active,
            required_skills=sorted(skills),
            created_at=role.created_at
        )

    @staticmethod
    def list_roles(db) -> List[TargetRoleResponseSchema]:
        roles = []
        if hasattr(db, "target_roles"):
            roles = list(db.target_roles.values())
        elif hasattr(db, "query"):
            roles = db.query(TargetRole).all()

        results = []
        for r in roles:
            skills = []
            if hasattr(db, "role_skills"):
                skills = [rs.skill_id for rs in db.role_skills if rs.role_id == r.id]
            elif hasattr(db, "query"):
                skills = [rs.skill_id for rs in db.query(RoleSkill).filter(lambda rs: rs.role_id == r.id).all()]

            results.append(TargetRoleResponseSchema(
                id=r.id,
                name=r.name,
                description=r.description,
                is_active=r.is_active,
                required_skills=sorted(skills),
                created_at=r.created_at
            ))

        return sorted(results, key=lambda x: x.id)
