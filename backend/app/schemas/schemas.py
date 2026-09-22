from typing import List, Optional, Any, Dict
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

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
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)
    title: str
    company: str
    location: str
    description: str
    employer_id: Optional[int] = None

class JobResponseSchema(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)
    id: Optional[int] = None
    title: str
    company: str
    location: str
    description: str
    employer_id: Optional[int] = None
    extracted_skills: List[SkillExtractionItem] = Field(default_factory=list)
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))

class EmployerFeedbackCreateSchema(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)
    employer_id: int
    comments: str
    course_id: Optional[int] = None
    rating: Optional[int] = None

class EmployerFeedbackSignalItem(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)
    skill_id: str
    confidence_score: float
    trust_weight: float
    weighted_signal: float

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
    evidence_type: str
    strength: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

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
