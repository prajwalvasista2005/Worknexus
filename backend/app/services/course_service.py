from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.courses import Course
from app.schemas.course import CourseCreate, CourseUpdate


class CourseService:

    @staticmethod
    def create_course(
        db: Session,
        course_data: CourseCreate,
    ) -> Course:
        course = Course(
            course_id=course_data.course_id,
            name=course_data.name,
            description=course_data.description,
            department=course_data.department,
            semester=course_data.semester,
            is_active=course_data.is_active,
        )
        db.add(course)
        db.commit()
        db.refresh(course)
        return course

    @staticmethod
    def get_course_by_id(
        db: Session,
        id: int,
    ) -> Course | None:
        stmt = select(Course).where(Course.id == id)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_course_by_code(
        db: Session,
        course_id: str,
    ) -> Course | None:
        stmt = select(Course).where(Course.course_id == course_id)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_all_courses(
        db: Session,
        department: str | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Course]:
        stmt = select(Course)
        if department:
            stmt = stmt.where(Course.department == department)
        if is_active is not None:
            stmt = stmt.where(Course.is_active == is_active)
        stmt = stmt.order_by(Course.name).offset(skip).limit(limit)
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def update_course(
        db: Session,
        id: int,
        course_data: CourseUpdate,
    ) -> Course | None:
        course = CourseService.get_course_by_id(db, id=id)
        if not course:
            return None

        update_data = course_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(course, field, value)

        db.commit()
        db.refresh(course)
        return course

    @staticmethod
    def delete_course(
        db: Session,
        id: int,
    ) -> bool:
        course = CourseService.get_course_by_id(db, id=id)
        if not course:
            return False

        db.delete(course)
        db.commit()
        return True
