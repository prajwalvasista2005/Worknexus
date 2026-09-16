from datetime import datetime, timezone
from unittest.mock import MagicMock
from fastapi import HTTPException

from app.api.user_skills import add_user_skill, get_my_skills, delete_user_skill
from app.models.users import User
from app.models.skills import Skill
from app.models.user_skills import UserSkill
from app.schemas.user_skill import UserSkillCreate


def test_add_user_skill_success():
    mock_db = MagicMock()
    mock_user = User(
        id=1,
        email="student@example.com",
        hashed_password="hash",
        full_name="Student One",
        role="student",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    mock_skill = Skill(
        id=5,
        skill_id="SKL-05",
        name="Python",
        category="IT & Software",
        description="Python programming",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    # First execute: find skill -> mock_skill
    # Second execute: check existing user_skill -> None
    mock_exec_skill = MagicMock()
    mock_exec_skill.scalar_one_or_none.return_value = mock_skill
    mock_exec_existing = MagicMock()
    mock_exec_existing.scalar_one_or_none.return_value = None

    mock_db.execute.side_effect = [mock_exec_skill, mock_exec_existing]

    data = UserSkillCreate(
        skill_id=5,
        proficiency_level="intermediate",
        source="course_completion",
    )

    result = add_user_skill(skill_data=data, current_user=mock_user, db=mock_db)
    assert result.user_id == 1
    assert result.skill_id == 5
    assert result.proficiency_level == "intermediate"
    assert mock_db.add.called
    assert mock_db.commit.called


def test_add_user_skill_skill_not_found():
    mock_db = MagicMock()
    mock_user = User(
        id=1,
        email="student@example.com",
        hashed_password="hash",
        full_name="Student One",
        role="student",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    mock_exec = MagicMock()
    mock_exec.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_exec

    data = UserSkillCreate(skill_id=999)
    try:
        add_user_skill(skill_data=data, current_user=mock_user, db=mock_db)
        assert False, "Should have raised 404"
    except HTTPException as exc:
        assert exc.status_code == 404
        assert "does not exist" in exc.detail
