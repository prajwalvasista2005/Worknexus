import os
from pathlib import Path

class Settings:
    PROJECT_NAME: str = "WorkNexus / SkillMesh"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./worknexus.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "sih2026-worknexus-dev-secret-key-12345")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

settings = Settings()
