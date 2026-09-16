from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.schemas.course import CourseCreate, CourseUpdate, CourseResponse
from app.schemas.course_skill import CourseSkillResponse
from app.services.course_service import CourseService
from app.services.course_skill_service import CourseSkillService

router = APIRouter(
    prefix="/courses",
    tags=["Courses"],
)


@router.get(
    "/",
    response_model=list[CourseResponse],
    summary="List curriculum courses",
)
def get_courses(
    department: str | None = None,
    is_active: bool | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    return CourseService.get_all_courses(
        db=db,
        department=department,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{id}",
    response_model=CourseResponse,
    summary="Get course by ID",
)
def get_course(
    id: int,
    db: Session = Depends(get_db),
):
    course = CourseService.get_course_by_id(db=db, id=id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )
    return course


@router.post(
    "/",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new curriculum course",
)
def create_course(
    course_data: CourseCreate,
    db: Session = Depends(get_db),
):
    existing = CourseService.get_course_by_code(db=db, course_id=course_data.course_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Course with course_id '{course_data.course_id}' already exists",
        )
    return CourseService.create_course(db=db, course_data=course_data)


@router.put(
    "/{id}",
    response_model=CourseResponse,
    summary="Update course details",
)
def update_course(
    id: int,
    course_data: CourseUpdate,
    db: Session = Depends(get_db),
):
    course = CourseService.update_course(db=db, id=id, course_data=course_data)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )
    return course


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a course",
)
def delete_course(
    id: int,
    db: Session = Depends(get_db),
):
    deleted = CourseService.delete_course(db=db, id=id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )
    return {"message": "Course deleted successfully"}


@router.get(
    "/{id}/skills",
    response_model=list[CourseSkillResponse],
    summary="Get all skills associated with a course",
)
def get_course_skills(
    id: int,
    db: Session = Depends(get_db),
):
    course = CourseService.get_course_by_id(db=db, id=id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )
    return CourseSkillService.get_course_skills(db=db, course_id=id)
