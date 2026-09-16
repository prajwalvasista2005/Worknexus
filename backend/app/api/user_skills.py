from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models.users import User
from app.schemas.user_skill import UserSkillCreate, UserSkillUpdate, UserSkillResponse
from app.services.user_skill_service import UserSkillService
from app.services.skill_service import SkillService

router = APIRouter(
    prefix="/user-skills",
    tags=["User Skills"],
)


@router.get(
    "/me",
    response_model=list[UserSkillResponse],
    summary="Get authenticated user's skills",
)
def get_my_skills(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return UserSkillService.get_user_skills(db=db, user_id=current_user.id)


@router.get(
    "/",
    response_model=list[UserSkillResponse],
    summary="List user skills (optionally filter by user_id)",
)
def get_user_skills(
    user_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target_user_id = user_id if user_id is not None else current_user.id
    return UserSkillService.get_user_skills(db=db, user_id=target_user_id)


@router.get(
    "/{id}",
    response_model=UserSkillResponse,
    summary="Get user skill record by ID",
)
def get_user_skill(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_skill = UserSkillService.get_user_skill_by_id(db=db, id=id)
    if not user_skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User skill record not found",
        )
    return user_skill


@router.post(
    "/",
    response_model=UserSkillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a skill to the authenticated user profile",
)
def add_user_skill(
    skill_data: UserSkillCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify skill exists
    skill = SkillService.get_skill_by_id(db=db, skill_id=skill_data.skill_id)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill with id {skill_data.skill_id} does not exist",
        )

    # Check for duplicate
    existing = UserSkillService.get_user_skill_by_user_and_skill(
        db=db,
        user_id=current_user.id,
        skill_id=skill_data.skill_id,
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skill already added to user profile",
        )

    return UserSkillService.add_user_skill(
        db=db,
        user_id=current_user.id,
        skill_data=skill_data,
    )


@router.put(
    "/{id}",
    response_model=UserSkillResponse,
    summary="Update proficiency or source of a user skill",
)
def update_user_skill(
    id: int,
    data: UserSkillUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_skill = UserSkillService.get_user_skill_by_id(db=db, id=id)
    if not user_skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User skill record not found",
        )
    if user_skill.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this user skill",
        )

    return UserSkillService.update_user_skill(db=db, id=id, data=data)


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Remove a skill from user profile",
)
def delete_user_skill(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_skill = UserSkillService.get_user_skill_by_id(db=db, id=id)
    if not user_skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User skill record not found",
        )
    if user_skill.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user skill",
        )

    UserSkillService.delete_user_skill(db=db, id=id)
    return {"message": "User skill removed successfully"}
