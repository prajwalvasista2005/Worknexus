from dotenv import load_dotenv
import os
import urllib.parse
from pathlib import Path

_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()

class Settings:
    PROJECT_NAME: str = "WorkNexus / SkillMesh"
    API_V1_STR: str = "/api/v1"

    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    _db_user = os.getenv("DB_USER")
    _db_pass = os.getenv("DB_PASSWORD")
    _db_host = os.getenv("DB_HOST", "localhost")
    _db_port = os.getenv("DB_PORT", "5432")
    _db_name = os.getenv("DB_NAME", "SkillSync")

    _raw_url = os.getenv("DATABASE_URL")
    _target_host = _db_host
    if _raw_url:
        try:
            parsed = urllib.parse.urlparse(_raw_url)
            if parsed.hostname:
                _target_host = parsed.hostname
        except Exception:
            pass

    _can_resolve_host = True
    if _target_host and _target_host not in ("localhost", "127.0.0.1"):
        try:
            import socket
            socket.gethostbyname(_target_host)
        except Exception:
            _can_resolve_host = False

    if _raw_url and ":password@db" not in _raw_url and _can_resolve_host:
        DATABASE_URL = _raw_url
    elif _db_user and _db_pass and _can_resolve_host:
        _encoded_pass = urllib.parse.quote_plus(_db_pass)
        DATABASE_URL = f"postgresql://{_db_user}:{_encoded_pass}@{_db_host}:{_db_port}/{_db_name}"
    else:
        DATABASE_URL = "sqlite:///./test.db"

    SECRET_KEY: str = os.getenv("SECRET_KEY", "default-dev-secret-key-replace-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")

    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )

    REFRESH_TOKEN_EXPIRE_DAYS: int = int(
        os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
    )

settings = Settings()