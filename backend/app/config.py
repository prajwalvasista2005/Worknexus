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

    DB_USER: str = os.getenv("DB_USER") or os.getenv("POSTGRES_USER") or "postgres"
    DB_PASSWORD: str = os.getenv("DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD") or "postgres"
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME") or os.getenv("POSTGRES_DB", "SkillSync")

    _db_user = DB_USER
    _db_pass = DB_PASSWORD
    _db_host = DB_HOST
    _db_port = DB_PORT
    _db_name = DB_NAME

    @staticmethod
    def _sanitize_url(url: str) -> str:
        """
        Sanitize database connection URL by ensuring special characters (e.g. '@')
        in credentials are safely URL-encoded to avoid splitting errors.
        """
        if not url or "://" not in url:
            return url
        prefix, _, host_part = url.rpartition("@")
        if "://" in prefix:
            scheme, _, user_pass = prefix.partition("://")
            if ":" in user_pass:
                user, _, password = user_pass.partition(":")
                encoded_password = urllib.parse.quote_plus(urllib.parse.unquote(password))
                encoded_user = urllib.parse.quote_plus(urllib.parse.unquote(user))
                return f"{scheme}://{encoded_user}:{encoded_password}@{host_part}"
        return url

    _raw_url = os.getenv("DATABASE_URL")
    if _raw_url:
        _raw_url = _sanitize_url(_raw_url)

    _can_resolve_raw = False
    if _raw_url and ":password@db" not in _raw_url:
        try:
            parsed = urllib.parse.urlparse(_raw_url)
            raw_host = parsed.hostname
            is_in_docker = DB_HOST == "db" or Path("/.dockerenv").exists()
            if raw_host in ("localhost", "127.0.0.1"):
                _can_resolve_raw = not is_in_docker
            elif raw_host == "db":
                _can_resolve_raw = True
            elif raw_host:
                import socket
                socket.gethostbyname(raw_host)
                _can_resolve_raw = True
        except Exception:
            _can_resolve_raw = False

    _can_resolve_db_host = False
    if DB_HOST:
        if DB_HOST in ("localhost", "127.0.0.1") or DB_HOST == "db":
            _can_resolve_db_host = True
        else:
            try:
                import socket
                socket.gethostbyname(DB_HOST)
                _can_resolve_db_host = True
            except Exception:
                _can_resolve_db_host = False

    if _can_resolve_raw and _raw_url:
        DATABASE_URL = _raw_url
    elif DB_USER and DB_PASSWORD and _can_resolve_db_host:
        _encoded_user = urllib.parse.quote_plus(urllib.parse.unquote(DB_USER))
        _encoded_pass = urllib.parse.quote_plus(urllib.parse.unquote(DB_PASSWORD))
        DATABASE_URL = f"postgresql://{_encoded_user}:{_encoded_pass}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
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

    _env_origins = os.getenv("ALLOWED_ORIGINS") or os.getenv("CORS_ORIGINS") or ""
    _custom_cors = [x.strip() for x in _env_origins.split(",") if x.strip()]
    if (os.getenv("ENVIRONMENT", "development").lower() in ("production", "prod")) and _custom_cors:
        CORS_ORIGINS: list[str] = _custom_cors
    else:
        CORS_ORIGINS: list[str] = list(set([
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ] + _custom_cors))
    ALLOWED_ORIGINS: list[str] = CORS_ORIGINS
    RATE_LIMITING_ENABLED: bool = os.getenv("RATE_LIMITING_ENABLED", "true").lower() in ("true", "1", "yes")

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
