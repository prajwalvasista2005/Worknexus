from datetime import datetime, timezone
from unittest.mock import MagicMock
from fastapi import HTTPException

from app.api.course_skills import add_skill_to_course, delete_course_skill
from app.models.courses import Course
from app.models.skills import Skill
from app.models.course_skills import CourseSkill
from app.schemas.course_skill import CourseSkillCreate


def test_add_skill_to_course_success():
    mock_db = MagicMock()
    mock_course = Course(
        id=1,
        course_id="CRS-01",
        name="Data Analytics",
        department="IT",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    mock_skill = Skill(
        id=2,
        skill_id="SKL-02",
        name="SQL",
        category="IT",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    mock_exec_course = MagicMock()
    mock_exec_course.scalar_one_or_none.return_value = mock_course
    mock_exec_skill = MagicMock()
    mock_exec_skill.scalar_one_or_none.return_value = mock_skill
    mock_exec_existing = MagicMock()
    mock_exec_existing.scalar_one_or_none.return_value = None

    mock_db.execute.side_effect = [mock_exec_course, mock_exec_skill, mock_exec_existing]

    data = CourseSkillCreate(course_id=1, skill_id=2)
    result = add_skill_to_course(data=data, db=mock_db)

    assert result.course_id == 1
    assert result.skill_id == 2
    assert mock_db.add.called
    assert mock_db.commit.called


def test_add_skill_to_course_course_not_found():
    mock_db = MagicMock()
    mock_exec = MagicMock()
    mock_exec.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_exec

    data = CourseSkillCreate(course_id=999, skill_id=1)
    try:
        add_skill_to_course(data=data, db=mock_db)
        assert False, "Should have raised 404"
    except HTTPException as exc:
        assert exc.status_code == 404
        assert "not found" in exc.detail
