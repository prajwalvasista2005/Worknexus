from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.schemas.skill import SkillCreate, SkillUpdate, SkillResponse
from app.services.skill_service import SkillService

router = APIRouter(
    prefix="/skills",
    tags=["Skills"],
)


@router.get(
    "/",
    response_model=list[SkillResponse],
    summary="List all skills",
)
def get_skills(
    category: str | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
):
    return SkillService.get_all_skills(db, category=category, is_active=is_active)


@router.get(
    "/{skill_id}",
    response_model=SkillResponse,
    summary="Get skill by ID",
)
def get_skill(
    skill_id: int,
    db: Session = Depends(get_db),
):
    skill = SkillService.get_skill_by_id(db=db, skill_id=skill_id)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found",
        )
    return skill


@router.post(
    "/",
    response_model=SkillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new skill",
)
def create_skill(
    skill_data: SkillCreate,
    db: Session = Depends(get_db),
):
    existing = SkillService.get_skill_by_code(db=db, skill_code=skill_data.skill_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Skill with code '{skill_data.skill_id}' already exists",
        )
    return SkillService.create_skill(db=db, skill_data=skill_data)


@router.put(
    "/{skill_id}",
    response_model=SkillResponse,
    summary="Update skill details",
)
def update_skill(
    skill_id: int,
    skill_data: SkillUpdate,
    db: Session = Depends(get_db),
):
    updated = SkillService.update_skill(db=db, skill_id=skill_id, skill_data=skill_data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found",
        )
    return updated


@router.delete(
    "/{skill_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a skill",
)
def delete_skill(
    skill_id: int,
    db: Session = Depends(get_db),
):
    deleted = SkillService.delete_skill(db=db, skill_id=skill_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found",
        )
    return {"message": "Skill deleted successfully"}