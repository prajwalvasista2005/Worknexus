from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")
    full_name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(default="student", description="Role: student, employer, institute, trainer")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"student", "employer", "institute", "trainer"}
        normalized = v.strip().lower()
        if normalized == "admin":
            raise ValueError("Admin accounts cannot be self-registered.")
        if normalized not in allowed:
            raise ValueError(f"Role must be one of: {sorted(list(allowed))}")
        return normalized


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
