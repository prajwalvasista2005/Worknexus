from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

@dataclass
class JobRecord:
    """
    Internal normalized representation for a job posting.
    Independent of database models or FastAPI schemas.
    """
    source: str
    source_record_id: str
    title: str
    description: str
    company: str
    location: str
    posted_at: Optional[str] = None
    work_type: Optional[str] = None
    explicit_skills: List[str] = field(default_factory=list)
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobRecord":
        return cls(
            source=data.get("source", ""),
            source_record_id=str(data.get("source_record_id", "")),
            title=data.get("title", ""),
            description=data.get("description", ""),
            company=data.get("company", ""),
            location=data.get("location", ""),
            posted_at=data.get("posted_at"),
            work_type=data.get("work_type"),
            explicit_skills=data.get("explicit_skills", []),
            raw_metadata=data.get("raw_metadata", {})
        )

@dataclass
class DeduplicatedJobRecord:
    """
    Represents a unified job posting resulting from conservative deduplication.
    Retains complete source provenance.
    """
    canonical_id: str
    title: str
    description: str
    company: str
    location: str
    posted_at: Optional[str] = None
    work_type: Optional[str] = None
    explicit_skills: List[str] = field(default_factory=list)
    source_records: List[Dict[str, str]] = field(default_factory=list)
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
