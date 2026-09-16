from datetime import datetime, timezone
from unittest.mock import MagicMock
from fastapi import HTTPException

from app.api.courses import get_courses, get_course, create_course, update_course, delete_course
from app.models.courses import Course
from app.schemas.course import CourseCreate, CourseUpdate


def test_create_course():
    mock_db = MagicMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_execute

    data = CourseCreate(
        course_id="CRS-TEST-01",
        name="Test Course in AI",
        description="Foundations of Machine Learning",
        department="AI & Data Science",
        semester="Semester 1",
        is_active=True,
    )
    result = create_course(course_data=data, db=mock_db)
    assert result.course_id == "CRS-TEST-01"
    assert result.name == "Test Course in AI"
    assert mock_db.add.called
    assert mock_db.commit.called


def test_get_course_not_found():
    mock_db = MagicMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_execute

    try:
        get_course(id=999, db=mock_db)
        assert False, "Should have raised 404"
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "Course not found"


def test_get_course_success():
    mock_db = MagicMock()
    course = Course(
        id=1,
        course_id="CRS-01",
        name="Data Analytics",
        description="Comprehensive Data Analytics",
        department="IT & Software",
        semester="Semester 1",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = course
    mock_db.execute.return_value = mock_execute

    result = get_course(id=1, db=mock_db)
    assert result.id == 1
    assert result.name == "Data Analytics"


def test_delete_course_success():
    mock_db = MagicMock()
    course = Course(
        id=1,
        course_id="CRS-01",
        name="Data Analytics",
        department="IT & Software",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = course
    mock_db.execute.return_value = mock_execute

    result = delete_course(id=1, db=mock_db)
    assert result == {"message": "Course deleted successfully"}
    assert mock_db.delete.called
    assert mock_db.commit.called
