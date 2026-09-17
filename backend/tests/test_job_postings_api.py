from datetime import datetime, timezone
from unittest.mock import MagicMock
from fastapi import HTTPException

from app.api.job_postings import (
    create_job_posting,
    get_job_posting,
    get_job_postings,
    delete_job_posting,
)
from app.models.job_postings import JobPosting
from app.schemas.job_postings import JobPostingCreate


def test_create_job_posting():
    mock_db = MagicMock()

    data = JobPostingCreate(
        title="Software Engineer",
        company_name="TechCorp",
        description="Develop scalable backend applications",
        location="Bengaluru, India",
        source="LinkedIn",
        posted_date=datetime.now(timezone.utc),
    )
    result = create_job_posting(job_data=data, db=mock_db)
    assert result.title == "Software Engineer"
    assert result.company_name == "TechCorp"
    assert result.description == "Develop scalable backend applications"
    assert mock_db.add.called
    assert mock_db.commit.called


def test_get_job_posting_not_found():
    mock_db = MagicMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_execute

    try:
        get_job_posting(job_id=999, db=mock_db)
        assert False, "Should have raised 404"
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "Job posting not found"


def test_get_job_posting_success():
    mock_db = MagicMock()
    job = JobPosting(
        id=1,
        title="Data Engineer",
        company_name="DataCorp",
        description="Build ETL pipelines",
        location="Remote",
        source="Company Portal",
        posted_date=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = job
    mock_db.execute.return_value = mock_execute

    result = get_job_posting(job_id=1, db=mock_db)
    assert result.id == 1
    assert result.title == "Data Engineer"
    assert result.company_name == "DataCorp"


def test_get_all_job_postings():
    mock_db = MagicMock()
    job = JobPosting(
        id=1,
        title="ML Engineer",
        company_name="AICorp",
        description="Deploy models",
        location="Hyderabad",
        source="Naukri",
        posted_date=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    mock_execute = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [job]
    mock_execute.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_execute

    results = get_job_postings(skip=0, limit=10, db=mock_db)
    assert len(results) == 1
    assert results[0].title == "ML Engineer"


def test_delete_job_posting_not_found():
    mock_db = MagicMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_execute

    try:
        delete_job_posting(job_id=999, db=mock_db)
        assert False, "Should have raised 404"
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "Job posting not found"


def test_delete_job_posting_success():
    mock_db = MagicMock()
    job = JobPosting(
        id=1,
        title="Data Engineer",
        company_name="DataCorp",
        description="Build ETL pipelines",
        location="Remote",
        source="Company Portal",
        posted_date=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = job
    mock_db.execute.return_value = mock_execute

    result = delete_job_posting(job_id=1, db=mock_db)
    assert result == {"message": "Job posting deleted successfully"}
    assert mock_db.delete.called
    assert mock_db.commit.called
