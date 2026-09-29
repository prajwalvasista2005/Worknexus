from dotenv import load_dotenv
import os
import urllib.parse
from pathlib import Path

_root_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _root_env_path.exists():
    load_dotenv(dotenv_path=_root_env_path)
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path, override=False)
else:
    load_dotenv()


INSECURE_SECRET_KEYS = {
    "default-dev-secret-key-replace-in-production",
    "default-dev-refresh-secret-key-replace-in-production",
    "secret",
    "secretkey",
    "changeme",
    "password",
    "insecure",
    "testsecret",
    "admin",
    "123456",
}


class Settings:
    PROJECT_NAME: str = "WorkNexus / SkillMesh"
    API_V1_STR: str = "/api/v1"

    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    _db_user = os.getenv("DB_USER") or os.getenv("POSTGRES_USER")
    _db_pass = os.getenv("DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD")
    _db_host = os.getenv("DB_HOST", "localhost")
    _db_port = os.getenv("DB_PORT", "5432")
    _db_name = os.getenv("DB_NAME") or os.getenv("POSTGRES_DB", "SkillSync")

    _raw_url = os.getenv("DATABASE_URL")

    _can_resolve_raw = False
    if _raw_url and ":password@db" not in _raw_url:
        try:
            parsed = urllib.parse.urlparse(_raw_url)
            raw_host = parsed.hostname
            if raw_host in ("localhost", "127.0.0.1"):
                _can_resolve_raw = True
            elif raw_host == "db" and not Path("/.dockerenv").exists():
                _can_resolve_raw = False
            elif raw_host:
                import socket
                socket.gethostbyname(raw_host)
                _can_resolve_raw = True
        except Exception:
            _can_resolve_raw = False

    _can_resolve_db_host = False
    if _db_host:
        if _db_host in ("localhost", "127.0.0.1"):
            _can_resolve_db_host = True
        else:
            try:
                import socket
                socket.gethostbyname(_db_host)
                _can_resolve_db_host = True
            except Exception:
                _can_resolve_db_host = False

    if _can_resolve_raw:
        DATABASE_URL = _raw_url
    elif _db_user and _db_pass and _can_resolve_db_host:
        _encoded_user = urllib.parse.quote(_db_user, safe="")
        _encoded_pass = urllib.parse.quote(_db_pass, safe="")
        DATABASE_URL = f"postgresql://{_encoded_user}:{_encoded_pass}@{_db_host}:{_db_port}/{_db_name}"
    else:
        DATABASE_URL = "sqlite:///./test.db"

    # Core Cryptographic & Token Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY", "default-dev-secret-key-replace-in-production")
    REFRESH_SECRET_KEY: str = os.getenv(
        "REFRESH_SECRET_KEY",
        os.getenv("SECRET_KEY", "default-dev-refresh-secret-key-replace-in-production")
    )
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")

    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )

    REFRESH_TOKEN_EXPIRE_DAYS: int = int(
        os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
    )

    _custom_cors = [x.strip() for x in os.getenv("CORS_ORIGINS", "").split(",") if x.strip()]
    CORS_ORIGINS: list[str] = list(set([
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ] + _custom_cors))

    def validate_production_security(self) -> None:
        """
        Enforce strict security validation for production environments:
        Refuses to start if SECRET_KEY or REFRESH_SECRET_KEY are unset, empty,
        shorter than 16 characters, or match known insecure defaults.
        """
        env = (self.ENVIRONMENT or "").strip().lower()
        if env in ("production", "prod"):
            if not self.SECRET_KEY or self.SECRET_KEY in INSECURE_SECRET_KEYS or len(self.SECRET_KEY) < 16:
                raise RuntimeError(
                    "FATAL SECURITY VIOLATION: Insecure or default SECRET_KEY detected in production environment. "
                    "A secure, randomly generated SECRET_KEY (min 16 characters) must be configured."
                )
            if not self.REFRESH_SECRET_KEY or self.REFRESH_SECRET_KEY in INSECURE_SECRET_KEYS or len(self.REFRESH_SECRET_KEY) < 16:
                raise RuntimeError(
                    "FATAL SECURITY VIOLATION: Insecure or default REFRESH_SECRET_KEY detected in production environment. "
                    "A secure, randomly generated REFRESH_SECRET_KEY (min 16 characters) must be configured."
                )


settings = Settings()