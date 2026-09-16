from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.schemas.course_skill import CourseSkillCreate, CourseSkillResponse
from app.services.course_skill_service import CourseSkillService
from app.services.course_service import CourseService
from app.services.skill_service import SkillService

router = APIRouter(
    prefix="/course-skills",
    tags=["Course Skills"],
)


@router.get(
    "/",
    response_model=list[CourseSkillResponse],
    summary="List course-skill mappings",
)
def get_course_skills(
    course_id: int | None = None,
    skill_id: int | None = None,
    db: Session = Depends(get_db),
):
    return CourseSkillService.get_course_skills(
        db=db,
        course_id=course_id,
        skill_id=skill_id,
    )


@router.get(
    "/{id}",
    response_model=CourseSkillResponse,
    summary="Get course-skill mapping by ID",
)
def get_course_skill(
    id: int,
    db: Session = Depends(get_db),
):
    mapping = CourseSkillService.get_course_skill_by_id(db=db, id=id)
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course-skill mapping not found",
        )
    return mapping


@router.post(
    "/",
    response_model=CourseSkillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Map a skill to a curriculum course",
)
def add_skill_to_course(
    data: CourseSkillCreate,
    db: Session = Depends(get_db),
):
    # Verify course exists
    course = CourseService.get_course_by_id(db=db, id=data.course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {data.course_id} not found",
        )

    # Verify skill exists
    skill = SkillService.get_skill_by_id(db=db, skill_id=data.skill_id)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill with id {data.skill_id} not found",
        )

    # Check for duplicate
    existing = CourseSkillService.get_course_skill(
        db=db,
        course_id=data.course_id,
        skill_id=data.skill_id,
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skill is already mapped to this course",
        )

    return CourseSkillService.add_skill_to_course(db=db, data=data)


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Remove a skill mapping from a course",
)
def delete_course_skill(
    id: int,
    db: Session = Depends(get_db),
):
    deleted = CourseSkillService.delete_course_skill(db=db, id=id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course-skill mapping not found",
        )
    return {"message": "Skill mapping removed from course successfully"}
