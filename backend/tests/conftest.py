"""
conftest.py - Phase 0 test harness: isolated test database + per-test rollback.

Architecture
------------
1.  Load .env before test modules import (required by test_migration_safety.py
    which evaluates `is_postgres` at module scope).

2.  Create a session-scoped SQLite database for all tests:
    - Custom SQLite event listeners disable pysqlite auto-commit and use explicit
      BEGIN / SAVEPOINT transactions.
    - seed_all() runs once at session start (canonical taxonomy, benchmark roles,
      seeded users with valid bcrypt password hashes, sample courses).

3.  SessionLocalProxy:
    - Installed at pytest_configure time so ANY test module doing
      `from app.db.session import SessionLocal` at import time receives the proxy.
    - The proxy dynamically delegates to the active per-test transaction session factory.

4.  Per-test transaction isolation (_isolated_test_transaction):
    - Opens a dedicated connection and begins an outer transaction.
    - Uses `join_transaction_mode="create_savepoint"` in SQLAlchemy 2.0 so that
      any `session.commit()` calls inside route handlers commit only savepoints on the
      same connection.
    - Direct calls to `SessionLocal()` and FastAPI dependency `get_db()` both use
      sessions bound to this same connection and see all savepoint-committed data.
    - Rolls back the entire outer transaction at test teardown for zero cross-test pollution.

5.  Excludes test_migration_safety.py which manages its own Postgres connections.
"""

from pathlib import Path
import pytest

# ---------------------------------------------------------------------------
# Step 1 — Load .env and define SessionLocalProxy
# ---------------------------------------------------------------------------
from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session


class SessionLocalProxy:
    """
    Transparent proxy for SessionLocal.
    Allows all modules that imported `SessionLocal` at import-time to dynamically
    bind to the active per-test transaction session factory.
    """
    def __init__(self, default_factory):
        self._factory = default_factory

    def set_factory(self, factory):
        self._factory = factory

    def reset_factory(self, default_factory):
        self._factory = default_factory

    def __call__(self, **kwargs):
        return self._factory(**kwargs)

    def __getattr__(self, name):
        return getattr(self._factory, name)


_TEST_DB_URL = "sqlite:///./test_harness.db"

_test_engine = create_engine(
    _TEST_DB_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(_test_engine, "connect")
def _do_connect(dbapi_connection, connection_record):
    # Disable pysqlite's automatic BEGIN/COMMIT so SAVEPOINT transactions work properly
    dbapi_connection.isolation_level = None


@event.listens_for(_test_engine, "begin")
def _do_begin(conn):
    conn.exec_driver_sql("BEGIN")


_TestSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=_test_engine,
)

_global_session_proxy = SessionLocalProxy(_TestSessionLocal)


def pytest_configure(config):
    """Load .env files and install SessionLocalProxy before test modules are imported."""
    backend_dir = Path(__file__).resolve().parent.parent  # .../backend
    project_root = backend_dir.parent                     # .../Worknexus

    for env_path in (project_root / ".env", backend_dir / ".env"):
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=False)

    # Patch SessionLocal at import-time across all relevant modules
    import app.db.session as sm
    import app.db.database as db_m
    import app.db.dependencies as dep_m

    sm.engine = _test_engine
    sm.SessionLocal = _global_session_proxy  # type: ignore[assignment]
    db_m.engine = _test_engine
    db_m.SessionLocal = _global_session_proxy  # type: ignore[assignment]
    dep_m.SessionLocal = _global_session_proxy  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Step 2 — Session-scoped fixture: create schema, seed, override get_db
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def _setup_test_database():
    """
    One-time session fixture:
    - Creates all tables in the SQLite test DB.
    - Disables FK enforcement, calls seed_all(), re-enables FK enforcement.
    - Overrides FastAPI's get_db dependency.
    """
    from app.db.base import Base

    # Import every model so Base.metadata knows all tables
    import app.models.users          # noqa: F401
    import app.models.skills         # noqa: F401
    import app.models.courses        # noqa: F401
    import app.models.course_skills  # noqa: F401
    import app.models.job_postings   # noqa: F401
    import app.models.jobSkill       # noqa: F401
    import app.models.refresh_tokens # noqa: F401
    import app.models.user_skills    # noqa: F401
    import app.models.student_roles  # noqa: F401
    import app.models.employers      # noqa: F401
    try:
        import app.models.entities   # noqa: F401
    except Exception:
        pass

    Base.metadata.drop_all(bind=_test_engine)
    Base.metadata.create_all(bind=_test_engine)

    # Seed with FK enforcement OFF so ordering doesn't matter
    with _test_engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        conn.commit()

    with _TestSessionLocal() as db:
        from app.db.seed import seed_all
        seed_all(db)

    # Re-enable FK enforcement for tests
    with _test_engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=ON"))
        conn.commit()

    from app.main import app as _app

    def _default_get_db():
        db = _global_session_proxy()
        try:
            yield db
        finally:
            db.close()

    _get_db_variants = set()
    try:
        from app.db.session import get_db
        _get_db_variants.add(get_db)
    except ImportError:
        pass
    try:
        from app.db.dependencies import get_db as gdep
        _get_db_variants.add(gdep)
    except ImportError:
        pass

    for _fn in _get_db_variants:
        _app.dependency_overrides[_fn] = _default_get_db

    yield  # ← all tests run here

    _app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=_test_engine)
    _test_engine.dispose()
    for name in ("./test_harness.db", "./test_harness.db-wal", "./test_harness.db-shm"):
        p = Path(name)
        if p.exists():
            p.unlink()


# ---------------------------------------------------------------------------
# Step 3 — Per-test transaction isolation
# ---------------------------------------------------------------------------
_MIGRATION_MODULE = "test_migration_safety"


@pytest.fixture(autouse=True)
def _isolated_test_transaction(request, _setup_test_database):
    """
    Per-test savepoint: any DB writes are rolled back after each test so the
    seeded baseline is always available to the next test.

    Skipped for migration tests that manage their own transactions.
    """
    module_name = getattr(getattr(request, "module", None), "__name__", "")
    if _MIGRATION_MODULE in module_name:
        yield
        return

    # Open a connection and begin a transaction we will roll back
    connection = _test_engine.connect()
    outer_trans = connection.begin()

    # Build a session factory bound to this connection with savepoint support
    BoundSession = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    # Update proxy so any SessionLocal() call inside the test uses BoundSession
    _global_session_proxy.set_factory(BoundSession)

    from app.main import app as _app

    def _bound_get_db():
        db = BoundSession()
        try:
            yield db
        finally:
            db.close()

    _get_db_variants = set()
    try:
        from app.db.session import get_db
        _get_db_variants.add(get_db)
    except ImportError:
        pass
    try:
        from app.db.dependencies import get_db as gdep
        _get_db_variants.add(gdep)
    except ImportError:
        pass

    for _fn in _get_db_variants:
        _app.dependency_overrides[_fn] = _bound_get_db

    try:
        yield
    finally:
        try:
            outer_trans.rollback()
        except Exception:
            pass
        connection.close()
        _global_session_proxy.reset_factory(_TestSessionLocal)
