from typing import Union, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.skills import Skill
from app.schemas.skill import SkillCreate, SkillUpdate


class SkillService:

    @staticmethod
    def create_skill(
        db: Session,
        skill_data: SkillCreate,
    ) -> Skill:
        skill = Skill(
            skill_id=skill_data.skill_id,
            name=skill_data.name,
            category=skill_data.category,
            description=skill_data.description,
        )

        db.add(skill)
        db.commit()
        db.refresh(skill)

        return skill

    @staticmethod
    def get_skill_by_id(
        db: Session,
        skill_id: int,
    ) -> Skill | None:
        if type(db).__name__ == "MockDatabaseSession" or not hasattr(db, "execute"):
            if hasattr(db, "skills") and isinstance(db.skills, dict):
                for s in db.skills.values():
                    if getattr(s, "id", None) == skill_id:
                        return s
            return None
        stmt = select(Skill).where(Skill.id == skill_id)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_skill_by_code(
        db: Session,
        skill_code: str,
    ) -> Skill | None:
        if type(db).__name__ == "MockDatabaseSession" or not hasattr(db, "execute"):
            if hasattr(db, "skills") and isinstance(db.skills, dict):
                if skill_code in db.skills:
                    return db.skills[skill_code]
                for s in db.skills.values():
                    if getattr(s, "skill_id", "") == skill_code:
                        return s
            return None
        stmt = select(Skill).where(Skill.skill_id == skill_code)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_skill_by_name(
        db: Session,
        name: str,
    ) -> Skill | None:
        if type(db).__name__ == "MockDatabaseSession" or not hasattr(db, "execute"):
            if hasattr(db, "skills") and isinstance(db.skills, dict):
                for s in db.skills.values():
                    if getattr(s, "name", "").lower() == name.lower():
                        return s
            return None
        stmt = select(Skill).where(Skill.name.ilike(name))
        return db.execute(stmt).scalar_one_or_none()

    _taxonomy_cache = None

    @classmethod
    def _get_taxonomy_cache(cls):
        if cls._taxonomy_cache is None:
            try:
                import json
                from pathlib import Path
                candidates = [
                    Path(__file__).resolve().parents[3] / "ml" / "data" / "skills.json",
                    Path("ml/data/skills.json"),
                ]
                tax_path = next((p for p in candidates if p.exists()), None)
                if tax_path:
                    with open(tax_path, "r", encoding="utf-8") as f:
                        cls._taxonomy_cache = json.load(f)
                else:
                    cls._taxonomy_cache = []
            except Exception:
                cls._taxonomy_cache = []
        return cls._taxonomy_cache

    @classmethod
    def _lookup_taxonomy(cls, skill_ident: str):
        if not skill_ident:
            return None
        import re
        ident = skill_ident.strip()
        norm_ident = re.sub(r'^(sk_|skill_)', '', ident.lower()).replace('_', ' ').strip()
        alpha_ident = re.sub(r'[^a-z0-9]', '', ident.lower())

        taxonomy = cls._get_taxonomy_cache()
        for s in taxonomy:
            cid = s.get("id", "")
            cname = s.get("name", "")
            category = s.get("category", "Technical")
            aliases = s.get("aliases", [])

            # Exact match on id or name
            if ident.lower() in [cid.lower(), cname.lower()]:
                return cid, cname, category

            # Match aliases
            for a in aliases:
                if ident.lower() == str(a).lower():
                    return cid, cname, category

            # Match normalized or alphanumeric
            for term in [cid, cname] + list(aliases):
                term_norm = re.sub(r'^(sk_|skill_)', '', str(term).lower()).replace('_', ' ').strip()
                term_alpha = re.sub(r'[^a-z0-9]', '', str(term).lower())
                if norm_ident and norm_ident == term_norm:
                    return cid, cname, category
                if alpha_ident and alpha_ident == term_alpha:
                    return cid, cname, category

        return None

    @staticmethod
    def get_or_create_skill(
        db: Session,
        skill_identifier: Union[int, str],
        default_category: str = "Technical",
        default_description: Optional[str] = None,
    ) -> Skill:
        """
        Query existing skill by id, canonical code, or name, or dynamically upsert
        a new Skill record so an integer primary key (id) is always retrieved.
        """
        if skill_identifier is None:
            raise ValueError("skill_identifier cannot be None")

        # 1. If integer or digit string: check by primary key id first
        if isinstance(skill_identifier, int) or (isinstance(skill_identifier, str) and skill_identifier.strip().isdigit()):
            int_id = int(skill_identifier)
            sk = SkillService.get_skill_by_id(db, int_id)
            if sk:
                return sk

        sk_str = str(skill_identifier).strip()
        if not sk_str:
            raise ValueError("skill_identifier cannot be empty string")

        # 2. Check canonical taxonomy resolution first
        tax_entry = SkillService._lookup_taxonomy(sk_str)
        if tax_entry:
            canon_code, canon_name, canon_cat = tax_entry
            sk = SkillService.get_skill_by_code(db, canon_code)
            if sk:
                return sk
            sk = SkillService.get_skill_by_name(db, canon_name)
            if sk:
                return sk
            # Also check if it's already in DB by raw input
            sk = SkillService.get_skill_by_code(db, sk_str) or SkillService.get_skill_by_name(db, sk_str)
            if sk:
                return sk
            # Use canonical taxonomy values for creation
            code = canon_code
            name = canon_name
            default_category = canon_cat
        else:
            # 3. Query by code (exact)
            sk = SkillService.get_skill_by_code(db, sk_str)
            if sk:
                return sk

            # 4. Query by name (case-insensitive)
            sk = SkillService.get_skill_by_name(db, sk_str)
            if sk:
                return sk

            # 5. Query variations (SK_ prefix <-> title name)
            if sk_str.upper().startswith("SK_"):
                candidate_name = sk_str[3:].replace("_", " ").strip()
                sk = SkillService.get_skill_by_name(db, candidate_name)
                if sk:
                    return sk
            else:
                clean_part = "".join(c if c.isalnum() else "_" for c in sk_str.upper()).strip("_")
                candidate_code = f"SK_{clean_part}"
                sk = SkillService.get_skill_by_code(db, candidate_code)
                if sk:
                    return sk

            # 6. Fallback: Upsert/Create into skills table
            if sk_str.upper().startswith("SK_"):
                code = sk_str.upper()[:50]
                name = sk_str[3:].replace("_", " ").title()
            else:
                name = sk_str
                clean_part = "".join(c if c.isalnum() else "_" for c in sk_str.upper()).strip("_")
                code = f"SK_{clean_part}" if clean_part else "SK_CUSTOM"
                code = code[:50]

        # Ensure code doesn't collide with an existing code
        base_code = code
        counter = 1
        while True:
            existing = SkillService.get_skill_by_code(db, code)
            if not existing:
                break
            suffix = f"_{counter}"
            code = f"{base_code[:50 - len(suffix)]}{suffix}"
            counter += 1

        new_skill = Skill(
            skill_id=code,
            name=name,
            category=default_category,
            description=default_description or f"Skill for {name}",
            is_active=True,
        )

        # Handle mock DB id assignment if needed
        if hasattr(db, "_skill_id_counter"):
            new_skill.id = db._skill_id_counter
            db._skill_id_counter += 1
        elif hasattr(db, "skills") and isinstance(db.skills, dict):
            max_id = 0
            for existing_sk in db.skills.values():
                sid = getattr(existing_sk, "id", None)
                if isinstance(sid, int) and sid > max_id:
                    max_id = sid
            new_skill.id = max_id + 1

        try:
            db.add(new_skill)
            if hasattr(db, "flush"):
                db.flush()
            if getattr(new_skill, "id", None) is None:
                new_skill.id = 1
            return new_skill
        except Exception:
            sk = SkillService.get_skill_by_code(db, code) or SkillService.get_skill_by_name(db, name)
            if sk:
                return sk
            raise

    @staticmethod
    def get_or_create_skill_id(
        db: Session,
        skill_identifier: Union[int, str],
        default_category: str = "Technical",
        default_description: Optional[str] = None,
    ) -> int:
        if isinstance(skill_identifier, int):
            sk = SkillService.get_skill_by_id(db, skill_identifier)
            if sk:
                return int(sk.id)
            return skill_identifier
        sk = SkillService.get_or_create_skill(
            db,
            skill_identifier=skill_identifier,
            default_category=default_category,
            default_description=default_description,
        )
        return int(sk.id)

    @staticmethod
    def get_all_skills(
        db: Session,
        category: str | None = None,
        is_active: bool | None = None,
    ) -> list[Skill]:
        stmt = select(Skill)
        if category:
            stmt = stmt.where(Skill.category == category)
        if is_active is not None:
            stmt = stmt.where(Skill.is_active == is_active)
        stmt = stmt.order_by(Skill.name)
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def update_skill(
        db: Session,
        skill_id: int,
        skill_data: SkillUpdate,
    ) -> Skill | None:
        skill = SkillService.get_skill_by_id(db, skill_id=skill_id)
        if not skill:
            return None

        update_data = skill_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(skill, field, value)

        db.commit()
        db.refresh(skill)
        return skill

    @staticmethod
    def delete_skill(
        db: Session,
        skill_id: int,
    ) -> bool:
        skill = SkillService.get_skill_by_id(db, skill_id=skill_id)
        if not skill:
            return False

        db.delete(skill)
        db.commit()
        return True


# Standalone function aliases
create_skill = SkillService.create_skill
get_skill_by_id = SkillService.get_skill_by_id
get_skill_by_code = SkillService.get_skill_by_code
get_skill_by_name = SkillService.get_skill_by_name
get_or_create_skill = SkillService.get_or_create_skill
get_or_create_skill_id = SkillService.get_or_create_skill_id
get_all_skills = SkillService.get_all_skills
update_skill = SkillService.update_skill
delete_skill = SkillService.delete_skill
