"""
conftest.py – Phase 0 test harness bootstrap.

Loads the project .env before any test module is imported so that
DATABASE_URL (and related vars) are present in os.environ at module-load
time.  This is required because test_migration_safety.py evaluates
`is_postgres` at module scope, before any fixture can run.

Postgres-relational and migration tests (test_migration_safety.py) are
conditionally skipped when no reachable PostgreSQL URL is provided;
they run automatically when DATABASE_URL resolves to a live PostgreSQL
instance (Docker / CI / local dev).
"""

from pathlib import Path

from dotenv import load_dotenv


def pytest_configure(config):
    """Load .env files before test modules are imported."""
    # Walk up from backend/ to the project root to find the canonical .env
    backend_dir = Path(__file__).resolve().parent.parent   # …/backend
    project_root = backend_dir.parent                      # …/Worknexus

    root_env = project_root / ".env"
    backend_env = backend_dir / ".env"

    if root_env.exists():
        load_dotenv(dotenv_path=root_env, override=False)
    if backend_env.exists():
        load_dotenv(dotenv_path=backend_env, override=False)
