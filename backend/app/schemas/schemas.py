from typing import List, Optional, Any, Dict
from datetime import datetime, timezone

try:
    from pydantic import BaseModel, Field
except ImportError:
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        def __getitem__(self, item):
            return getattr(self, item)
        def dict(self) -> Dict[str, Any]:
            res = {}
            for k, v in self.__dict__.items():
                if not k.startswith("_"):
                    if isinstance(v, list):
                        res[k] = [x.dict() if hasattr(x, "dict") else (x.__dict__ if hasattr(x, "__dict__") else x) for x in v]
                    elif hasattr(v, "dict"):
                        res[k] = v.dict()
                    elif hasattr(v, "__dict__"):
                        res[k] = v.__dict__
                    else:
                        res[k] = v
            return res
        def __repr__(self):
            return f"{self.__class__.__name__}({self.dict()})"

    def Field(default=None, **kwargs):
        return default

class SkillExtractionRequest(BaseModel):
    def __init__(self, text: str, **kwargs):
        if not text or not isinstance(text, str):
            raise ValueError("text must be a non-empty string")
        self.text = text
        super().__init__(**kwargs)

class SkillExtractionItem(BaseModel):
    def __init__(self, skill_id: str, confidence_score: float, **kwargs):
        self.skill_id = str(skill_id)
        self.confidence_score = float(confidence_score)
        super().__init__(**kwargs)

class SkillExtractionResponse(BaseModel):
    def __init__(self, skills: List[SkillExtractionItem], **kwargs):
        self.skills = skills
        super().__init__(**kwargs)

class JobCreateSchema(BaseModel):
    def __init__(self, title: str, company: str, location: str, description: str, employer_id: Optional[int] = None, **kwargs):
        self.title = str(title)
        self.company = str(company)
        self.location = str(location)
        self.description = str(description)
        self.employer_id = employer_id
        super().__init__(**kwargs)

class JobResponseSchema(BaseModel):
    def __init__(self, id: int, title: str, company: str, location: str, description: str, employer_id: Optional[int] = None, extracted_skills: Optional[List[SkillExtractionItem]] = None, created_at: Optional[datetime] = None, **kwargs):
        self.id = id
        self.title = title
        self.company = company
        self.location = location
        self.description = description
        self.employer_id = employer_id
        self.extracted_skills = extracted_skills or []
        self.created_at = created_at or datetime.now(timezone.utc)
        super().__init__(**kwargs)

class EmployerFeedbackCreateSchema(BaseModel):
    def __init__(self, employer_id: int, comments: str, course_id: Optional[int] = None, rating: Optional[int] = None, **kwargs):
        self.employer_id = int(employer_id)
        self.comments = str(comments)
        self.course_id = course_id
        self.rating = rating
        super().__init__(**kwargs)

class EmployerFeedbackSignalItem(BaseModel):
    def __init__(self, skill_id: str, confidence_score: float, trust_weight: float, weighted_signal: float, **kwargs):
        self.skill_id = str(skill_id)
        self.confidence_score = float(confidence_score)
        self.trust_weight = float(trust_weight)
        self.weighted_signal = float(weighted_signal)
        super().__init__(**kwargs)

class EmployerFeedbackResponseSchema(BaseModel):
    def __init__(self, id: int, employer_id: int, comments: str, course_id: Optional[int] = None, rating: Optional[int] = None, signals: Optional[List[EmployerFeedbackSignalItem]] = None, **kwargs):
        self.id = id
        self.employer_id = employer_id
        self.course_id = course_id
        self.comments = comments
        self.rating = rating
        self.signals = signals or []
        super().__init__(**kwargs)

# =====================================================================
# PHASE 10: CAREER ROLE & STUDENT PROFILE SCHEMAS
# =====================================================================

class RoleSkillItemSchema(BaseModel):
    def __init__(self, skill_id: str, **kwargs):
        self.skill_id = str(skill_id)
        super().__init__(**kwargs)

class TargetRoleCreateSchema(BaseModel):
    def __init__(self, id: str, name: str, description: Optional[str] = None, skill_ids: Optional[List[str]] = None, **kwargs):
        self.id = str(id)
        self.name = str(name)
        self.description = description
        self.skill_ids = skill_ids or []
        super().__init__(**kwargs)

class TargetRoleResponseSchema(BaseModel):
    def __init__(self, id: str, name: str, description: Optional[str] = None, is_active: bool = True, required_skills: Optional[List[str]] = None, created_at: Optional[datetime] = None, **kwargs):
        self.id = str(id)
        self.name = str(name)
        self.description = description
        self.is_active = is_active
        self.required_skills = required_skills or []
        self.created_at = created_at or datetime.now(timezone.utc)
        super().__init__(**kwargs)

class StudentSkillEvidenceCreateSchema(BaseModel):
    def __init__(self, skill_id: str, evidence_type: str, strength: str, metadata: Optional[Dict[str, Any]] = None, **kwargs):
        self.skill_id = str(skill_id)
        self.evidence_type = str(evidence_type)
        self.strength = str(strength)
        self.metadata = metadata or {}
        super().__init__(**kwargs)

class StudentSkillEvidenceResponseSchema(BaseModel):
    def __init__(self, id: int, student_profile_id: int, skill_id: str, evidence_type: str, strength: str, metadata: Optional[Dict[str, Any]] = None, created_at: Optional[datetime] = None, **kwargs):
        self.id = id
        self.student_profile_id = student_profile_id
        self.skill_id = skill_id
        self.evidence_type = evidence_type
        self.strength = strength
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.now(timezone.utc)
        super().__init__(**kwargs)

class StudentProfileCreateSchema(BaseModel):
    def __init__(self, user_id: int, target_role_id: Optional[str] = None, **kwargs):
        self.user_id = int(user_id)
        self.target_role_id = target_role_id
        super().__init__(**kwargs)

class StudentProfileResponseSchema(BaseModel):
    def __init__(self, id: int, user_id: int, target_role_id: Optional[str] = None, evidence_records: Optional[List[StudentSkillEvidenceResponseSchema]] = None, created_at: Optional[datetime] = None, **kwargs):
        self.id = id
        self.user_id = user_id
        self.target_role_id = target_role_id
        self.evidence_records = evidence_records or []
        self.created_at = created_at or datetime.now(timezone.utc)
        super().__init__(**kwargs)
