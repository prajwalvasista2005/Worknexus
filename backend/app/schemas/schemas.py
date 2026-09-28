from typing import List, Optional, Any, Dict
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict, model_validator

class SkillExtractionRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)
    text: str

class SkillExtractionItem(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)
    skill_id: str
    confidence_score: float

class SkillExtractionResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)
    skills: List[SkillExtractionItem] = Field(default_factory=list)

class JobCreateSchema(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True, populate_by_name=True)
    title: str = ""
    company: str = ""
    location: str = "Remote"
    description: str = ""
    employer_id: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_job_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Map alternate naming: job_title -> title
            if "job_title" in data and not data.get("title"):
                data["title"] = data["job_title"]
            elif "title" in data and not data.get("job_title"):
                data["job_title"] = data["title"]

            # Map alternate naming: company_name -> company
            if "company_name" in data and not data.get("company"):
                data["company"] = data["company_name"]
            elif "company" in data and not data.get("company_name"):
                data["company_name"] = data["company"]

            # Map alternate naming: comments / requirements -> description
            if "comments" in data and not data.get("description"):
                data["description"] = data["comments"]
            elif "description" in data and not data.get("comments"):
                data["comments"] = data["description"]

            # If required_skills provided as list or string, append to description for ML extraction
            req_skills = data.get("required_skills")
            if req_skills:
                skills_str = ", ".join(req_skills) if isinstance(req_skills, list) else str(req_skills)
                cur_desc = data.get("description", "")
                data["description"] = f"{cur_desc}\nRequired Skills: {skills_str}".strip()

            if not data.get("title"):
                data["title"] = "Engineering Role"
            if not data.get("company"):
                data["company"] = "WorkNexus Partner"
            if not data.get("description"):
                data["description"] = "Seeking qualified candidate with relevant technical competencies."
        return data

class JobResponseSchema(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)
    id: Optional[int] = None
    title: str
    company: str
    location: str
    description: str
    employer_id: Optional[int] = None
    extracted_skills: List[SkillExtractionItem] = Field(default_factory=list)
    confidence_scores: Optional[Dict[str, float]] = None
    skills: Optional[List[str]] = None
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))

class EmployerFeedbackCreateSchema(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)
    employer_id: Optional[int] = None
    comments: Optional[str] = None
    feedback_text: Optional[str] = None
    course_id: Optional[int] = None
    rating: Optional[int] = None

    def model_post_init(self, __context):
        if not self.comments and self.feedback_text:
            self.comments = self.feedback_text
        if not self.comments:
            self.comments = "General feedback"


class EmployerFeedbackSignalItem(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)
    id: Optional[int] = None
    skill_id: str
    confidence_score: float = 0.95
    trust_weight: float = 1.0
    weighted_signal: float = 0.95
    signal_type: Optional[str] = "employer_observation"
    sentiment_weight: Optional[float] = None
    confidence: Optional[float] = None

    def model_post_init(self, __context):
        if self.confidence is None:
            self.confidence = self.confidence_score
        if self.sentiment_weight is None:
            self.sentiment_weight = self.weighted_signal

class EmployerFeedbackResponseSchema(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)
    id: Optional[int] = None
    employer_id: int
    comments: str
    course_id: Optional[int] = None
    rating: Optional[int] = None
    signals: List[EmployerFeedbackSignalItem] = Field(default_factory=list)
    detected_signals: Optional[List[EmployerFeedbackSignalItem]] = None
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))

class EmployerProfileCreateSchema(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)
    company_name: str
    trust_weight: Optional[float] = 1.0

class EmployerProfileResponseSchema(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)
    id: int
    company_name: str
    trust_weight: float = 1.0
    user_id: Optional[int] = None
    created_at: Optional[datetime] = None

# =====================================================================
# PHASE 10: CAREER ROLE & STUDENT PROFILE SCHEMAS
# =====================================================================

class RoleSkillItemSchema(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)
    skill_id: str

class TargetRoleCreateSchema(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)
    id: str
    name: str
    description: Optional[str] = None
    skill_ids: List[str] = Field(default_factory=list)

class TargetRoleResponseSchema(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)
    id: str
    name: str
    description: Optional[str] = None
    is_active: bool = True
    required_skills: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))

class StudentSkillEvidenceCreateSchema(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)
    skill_id: str
    evidence_type: str = "project"
    strength: str = "intermediate"
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_evidence_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Normalize evidence_type
            ev_type = str(data.get("evidence_type", "")).strip().lower()
            type_mapping = {
                "github_pr": "project",
                "portfolio_project": "project",
                "coursework": "course_completed",
                "course": "course_completed",
                "quiz": "assessment",
                "exam": "assessment",
                "certificate": "certification",
            }
            if ev_type in type_mapping:
                data["evidence_type"] = type_mapping[ev_type]
            elif ev_type in {"self_reported", "course_completed", "project", "certification", "assessment"}:
                data["evidence_type"] = ev_type
            elif not ev_type:
                data["evidence_type"] = "self_reported"
            # Otherwise preserve original string so domain validation can raise ValueError

            # Normalize strength
            st_val = data.get("strength")
            if isinstance(st_val, (int, float)):
                if st_val >= 8:
                    data["strength"] = "advanced"
                elif st_val >= 5:
                    data["strength"] = "intermediate"
                else:
                    data["strength"] = "basic"
            elif isinstance(st_val, str):
                st_str = st_val.strip().lower()
                alias_map = {
                    "1": "basic", "2": "basic", "3": "basic", "4": "basic", "beginner": "basic", "low": "basic",
                    "5": "intermediate", "6": "intermediate", "7": "intermediate", "medium": "intermediate",
                    "8": "advanced", "9": "advanced", "10": "advanced", "high": "advanced", "expert": "advanced"
                }
                if st_str in alias_map:
                    data["strength"] = alias_map[st_str]
                elif st_str in {"basic", "intermediate", "advanced"}:
                    data["strength"] = st_str
                # Otherwise preserve original string so domain validation can raise ValueError
        return data

class StudentSkillEvidenceResponseSchema(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)
    id: Optional[int] = None
    student_profile_id: int
    skill_id: str
    evidence_type: str
    strength: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))

class StudentProfileCreateSchema(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)
    user_id: int
    target_role_id: Optional[str] = None

class StudentProfileResponseSchema(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)
    id: Optional[int] = None
    user_id: int
    target_role_id: Optional[str] = None
    evidence_records: List[StudentSkillEvidenceResponseSchema] = Field(default_factory=list)
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
