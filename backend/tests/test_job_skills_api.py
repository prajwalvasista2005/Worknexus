from datetime import datetime, timezone
from unittest.mock import MagicMock
from fastapi import HTTPException

from app.api.job_skills import (
    create_job_skill,
    get_job_skill,
    get_job_skills,
    delete_job_skill,
)
from app.models.job_postings import JobPosting
from app.models.jobSkill import JobSkill
from app.models.skills import Skill
from app.schemas.job_skills import JobSkillCreate


def test_create_job_skill_success():
    mock_db = MagicMock()
    mock_job = JobPosting(
        id=1,
        title="Backend Engineer",
        company_name="InnovateTech",
        description="FastAPI Dev",
        location="Remote",
        created_at=datetime.now(timezone.utc),
    )
    mock_skill = Skill(
        id=10,
        skill_id="SKL-PY-01",
        name="Python",
        category="IT",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    mock_exec_job = MagicMock()
    mock_exec_job.scalar_one_or_none.return_value = mock_job
    mock_exec_skill = MagicMock()
    mock_exec_skill.scalar_one_or_none.return_value = mock_skill
    mock_exec_existing = MagicMock()
    mock_exec_existing.scalar_one_or_none.return_value = None

    mock_db.execute.side_effect = [mock_exec_job, mock_exec_skill, mock_exec_existing]

    data = JobSkillCreate(job_id=1, skill_id="SKL-PY-01")
    result = create_job_skill(job_skill_data=data, db=mock_db)

    assert result.job_id == 1
    assert result.skill_id == "SKL-PY-01"
    assert mock_db.add.called
    assert mock_db.commit.called


def test_create_job_skill_job_not_found():
    mock_db = MagicMock()
    mock_exec = MagicMock()
    mock_exec.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_exec

    data = JobSkillCreate(job_id=999, skill_id="SKL-PY-01")
    try:
        create_job_skill(job_skill_data=data, db=mock_db)
        assert False, "Should have raised 404"
    except HTTPException as exc:
        assert exc.status_code == 404
        assert "Job posting with id 999 not found" in exc.detail


def test_create_job_skill_skill_not_found():
    mock_db = MagicMock()
    mock_job = JobPosting(
        id=1,
        title="Backend Engineer",
        company_name="InnovateTech",
        description="FastAPI Dev",
    )

    mock_exec_job = MagicMock()
    mock_exec_job.scalar_one_or_none.return_value = mock_job
    mock_exec_skill = MagicMock()
    mock_exec_skill.scalar_one_or_none.return_value = None

    mock_db.execute.side_effect = [mock_exec_job, mock_exec_skill]

    data = JobSkillCreate(job_id=1, skill_id="NON-EXISTENT")
    try:
        create_job_skill(job_skill_data=data, db=mock_db)
        assert False, "Should have raised 404"
    except HTTPException as exc:
        assert exc.status_code == 404
        assert "Skill with skill_id 'NON-EXISTENT' not found" in exc.detail


def test_create_job_skill_duplicate():
    mock_db = MagicMock()
    mock_job = JobPosting(
        id=1,
        title="Backend Engineer",
        company_name="InnovateTech",
        description="FastAPI Dev",
    )
    mock_skill = Skill(
        id=10,
        skill_id="SKL-PY-01",
        name="Python",
        category="IT",
    )
    existing_mapping = JobSkill(
        id=5,
        job_id=1,
        skill_id="SKL-PY-01",
    )

    mock_exec_job = MagicMock()
    mock_exec_job.scalar_one_or_none.return_value = mock_job
    mock_exec_skill = MagicMock()
    mock_exec_skill.scalar_one_or_none.return_value = mock_skill
    mock_exec_existing = MagicMock()
    mock_exec_existing.scalar_one_or_none.return_value = existing_mapping

    mock_db.execute.side_effect = [mock_exec_job, mock_exec_skill, mock_exec_existing]

    data = JobSkillCreate(job_id=1, skill_id="SKL-PY-01")
    try:
        create_job_skill(job_skill_data=data, db=mock_db)
        assert False, "Should have raised 400"
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "Skill is already mapped to this job posting" in exc.detail


def test_get_job_skill_not_found():
    mock_db = MagicMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_execute

    try:
        get_job_skill(job_skill_id=999, db=mock_db)
        assert False, "Should have raised 404"
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "Job skill mapping not found"


def test_get_job_skill_success():
    mock_db = MagicMock()
    mapping = JobSkill(
        id=1,
        job_id=1,
        skill_id="SKL-PY-01",
        created_at=datetime.now(timezone.utc),
    )
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mapping
    mock_db.execute.return_value = mock_execute

    result = get_job_skill(job_skill_id=1, db=mock_db)
    assert result.id == 1
    assert result.job_id == 1
    assert result.skill_id == "SKL-PY-01"


def test_get_all_job_skills():
    mock_db = MagicMock()
    mapping = JobSkill(
        id=1,
        job_id=1,
        skill_id="SKL-PY-01",
        created_at=datetime.now(timezone.utc),
    )
    mock_execute = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mapping]
    mock_execute.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_execute

    results = get_job_skills(job_id=1, db=mock_db)
    assert len(results) == 1
    assert results[0].skill_id == "SKL-PY-01"


def test_delete_job_skill_not_found():
    mock_db = MagicMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_execute

    try:
        delete_job_skill(job_skill_id=999, db=mock_db)
        assert False, "Should have raised 404"
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "Job skill mapping not found"


def test_delete_job_skill_success():
    mock_db = MagicMock()
    mapping = JobSkill(
        id=1,
        job_id=1,
        skill_id="SKL-PY-01",
        created_at=datetime.now(timezone.utc),
    )
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mapping
    mock_db.execute.return_value = mock_execute

    result = delete_job_skill(job_skill_id=1, db=mock_db)
    assert result == {"message": "Job skill mapping deleted successfully"}
    assert mock_db.delete.called
    assert mock_db.commit.called
