import os
from pathlib import Path
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from alembic.config import Config
from alembic import command


# Detect if PostgreSQL is available and reachable from environment
raw_url = os.getenv("DATABASE_URL", "")

def _check_postgres_available() -> bool:
    if not (raw_url and raw_url.startswith("postgresql")):
        return False
    try:
        import urllib.parse, socket
        parsed = urllib.parse.urlparse(raw_url)
        host = parsed.hostname
        if not host:
            return False
        if host == "db" and not Path("/.dockerenv").exists():
            return False
        socket.gethostbyname(host)
        test_eng = create_engine(raw_url, connect_args={"connect_timeout": 2})
        with test_eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

is_postgres = _check_postgres_available()


def get_postgres_url_with_schema(schema_name: str) -> str:
    """Constructs a PostgreSQL connection string scoped to a specific schema search_path."""
    base_url = raw_url
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}options=-csearch_path%3D{schema_name}"


def run_alembic_upgrade(target_url: str, revision: str = "head") -> None:
    """Executes a real Alembic upgrade against the specified database URL."""
    backend_dir = Path(__file__).resolve().parent.parent
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", target_url.replace("%", "%%"))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(alembic_cfg, revision)


def _get_migration_002():
    import importlib.util
    file_path = Path(__file__).resolve().parent.parent / "alembic" / "versions" / "002_add_user_id_to_employers.py"
    spec = importlib.util.spec_from_file_location("migration_002", file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ==============================================================================
# Fast Local SQLite Unit Tests
# ==============================================================================

def test_migration_002_aborts_on_ambiguous_unlinked_employer(tmp_path):
    """
    Verifies that migration 002 refuses to guess when an employer cannot be
    unambiguously mapped to a user, aborting loudly with an error listing the
    unmatched records.
    """
    db_path = tmp_path / "test_migration_abort.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                role VARCHAR(32) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.execute(text("""
            CREATE TABLE employers (
                id INTEGER PRIMARY KEY,
                company_name VARCHAR(255) NOT NULL,
                trust_weight FLOAT NOT NULL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.execute(text("""
            INSERT INTO users (id, email, hashed_password, full_name, role)
            VALUES (1, 'student@worknexus.io', 'hash', 'Alice Student', 'student'),
                   (2, 'other_emp@worknexus.io', 'hash', 'Acme Corp', 'employer');
        """))
        conn.execute(text("""
            INSERT INTO employers (id, company_name)
            VALUES (2, 'Acme Corp'),
                   (99, 'Orphaned Mystery Corp');
        """))

    migration_002 = _get_migration_002()
    from unittest.mock import patch, MagicMock

    with engine.connect() as conn:
        with patch.object(migration_002, "op") as mock_op:
            mock_op.get_bind.return_value = conn
            def add_col(t, col):
                conn.execute(text(f"ALTER TABLE {t} ADD COLUMN {col.name} INTEGER"))
            mock_op.add_column.side_effect = add_col
            mock_op.create_index = MagicMock()
            mock_op.create_foreign_key = MagicMock()
            with pytest.raises(RuntimeError) as exc_info:
                with conn.begin():
                    migration_002.upgrade()

            assert "Migration 002 aborted" in str(exc_info.value)
            assert "Orphaned Mystery Corp" in str(exc_info.value)
            assert "Do not guess" in str(exc_info.value)


def test_migration_002_succeeds_on_unambiguous_data(tmp_path):
    """
    Verifies that migration 002 correctly backfills user_id when matches are
    strictly unambiguous (e.g., exact 1:1 match by company_name or ID).
    """
    db_path = tmp_path / "test_migration_success.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                role VARCHAR(32) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.execute(text("""
            CREATE TABLE employers (
                id INTEGER PRIMARY KEY,
                company_name VARCHAR(255) NOT NULL,
                trust_weight FLOAT NOT NULL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.execute(text("""
            INSERT INTO users (id, email, hashed_password, full_name, role)
            VALUES (10, 'tech_corp@worknexus.io', 'hash', 'TechCorp International', 'employer');
        """))
        conn.execute(text("""
            INSERT INTO employers (id, company_name)
            VALUES (1, 'TechCorp International');
        """))

    migration_002 = _get_migration_002()
    from unittest.mock import patch, MagicMock

    with engine.connect() as conn:
        with patch.object(migration_002, "op") as mock_op:
            mock_op.get_bind.return_value = conn
            def add_col(t, col):
                conn.execute(text(f"ALTER TABLE {t} ADD COLUMN {col.name} INTEGER"))
            mock_op.add_column.side_effect = add_col
            mock_op.create_index = MagicMock()
            mock_op.create_foreign_key = MagicMock()
            with conn.begin():
                migration_002.upgrade()

        res = conn.execute(text("SELECT id, user_id, company_name FROM employers WHERE id = 1")).fetchone()
        assert res[1] == 10
        assert res[2] == "TechCorp International"


# ==============================================================================
# Real PostgreSQL-Backed Migration Tests (Exercises real indexes and FK constraints)
# ==============================================================================

@pytest.mark.skipif(not is_postgres, reason="Requires PostgreSQL database (DATABASE_URL)")
def test_postgres_migration_002_aborts_on_ambiguous_data():
    """
    Executes real 'alembic upgrade head' against PostgreSQL on ambiguous legacy data,
    asserting that migration 002 aborts loudly without guessing or corrupting data.
    """
    schema_name = "test_pg_abort_ambiguous"
    pg_target_url = get_postgres_url_with_schema(schema_name)
    engine = create_engine(raw_url)

    # Setup isolated PostgreSQL schema with legacy tables at 001_phase10
    with engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;"))
        conn.execute(text(f"CREATE SCHEMA {schema_name};"))
        conn.execute(text(f"""
            CREATE TABLE {schema_name}.alembic_version (version_num VARCHAR(32) PRIMARY KEY);
            INSERT INTO {schema_name}.alembic_version VALUES ('001_phase10');

            CREATE TABLE {schema_name}.users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) NOT NULL UNIQUE,
                hashed_password VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                role VARCHAR(32) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            CREATE TABLE {schema_name}.employers (
                id SERIAL PRIMARY KEY,
                company_name VARCHAR(255) NOT NULL,
                trust_weight FLOAT NOT NULL DEFAULT 1.0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            INSERT INTO {schema_name}.users (id, email, hashed_password, full_name, role)
            VALUES (1, 'u1@worknexus.io', 'hash', 'Alice Student', 'student'),
                   (2, 'u2@worknexus.io', 'hash', 'Acme Corp', 'employer');

            INSERT INTO {schema_name}.employers (id, company_name)
            VALUES (2, 'Acme Corp'),
                   (99, 'Orphaned Mystery Corp');
        """))

    try:
        # Running the real alembic upgrade head must fail loudly
        with pytest.raises(Exception) as exc_info:
            run_alembic_upgrade(pg_target_url, "head")

        err_msg = str(exc_info.value)
        assert "Migration 002 aborted" in err_msg or "Orphaned Mystery Corp" in err_msg
    finally:
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;"))


@pytest.mark.skipif(not is_postgres, reason="Requires PostgreSQL database (DATABASE_URL)")
def test_postgres_migration_002_succeeds_and_enforces_fk_and_unique_index():
    """
    Executes real 'alembic upgrade head' against PostgreSQL on unambiguous data,
    verifying that the migration succeeds, populates user_id, and strictly enforces
    PostgreSQL unique index and foreign key constraints.
    """
    schema_name = "test_pg_success_enforce"
    pg_target_url = get_postgres_url_with_schema(schema_name)
    engine = create_engine(raw_url)

    with engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;"))
        conn.execute(text(f"CREATE SCHEMA {schema_name};"))
        conn.execute(text(f"""
            CREATE TABLE {schema_name}.alembic_version (version_num VARCHAR(32) PRIMARY KEY);
            INSERT INTO {schema_name}.alembic_version VALUES ('001_phase10');

            CREATE TABLE {schema_name}.users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) NOT NULL UNIQUE,
                hashed_password VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                role VARCHAR(32) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            CREATE TABLE {schema_name}.employers (
                id SERIAL PRIMARY KEY,
                company_name VARCHAR(255) NOT NULL,
                trust_weight FLOAT NOT NULL DEFAULT 1.0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            INSERT INTO {schema_name}.users (id, email, hashed_password, full_name, role)
            VALUES (10, 'tech_corp@worknexus.io', 'hash', 'TechCorp International', 'employer');

            INSERT INTO {schema_name}.employers (id, company_name)
            VALUES (1, 'TechCorp International');
        """))

    try:
        # Run real alembic upgrade head
        run_alembic_upgrade(pg_target_url, "head")

        with engine.connect() as conn:
            # 1. Assert user_id is properly populated
            res = conn.execute(text(f"SELECT id, user_id, company_name FROM {schema_name}.employers WHERE id = 1")).fetchone()
            assert res[1] == 10
            assert res[2] == "TechCorp International"

            # 2. Assert PostgreSQL UNIQUE constraint on user_id
            with pytest.raises(IntegrityError):
                with conn.begin():
                    conn.execute(text(f"""
                        INSERT INTO {schema_name}.employers (id, user_id, company_name)
                        VALUES (2, 10, 'Duplicate Employer User')
                    """))

            # 3. Assert PostgreSQL FOREIGN KEY constraint referencing users(id)
            with pytest.raises(IntegrityError):
                with conn.begin():
                    conn.execute(text(f"""
                        INSERT INTO {schema_name}.employers (id, user_id, company_name)
                        VALUES (3, 999999, 'Nonexistent User')
                    """))
    finally:
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;"))


# ==============================================================================
# Real Migration Tests for Planned Hardening Phases (marked xfail until implemented)
# ==============================================================================

@pytest.mark.xfail(
    raises=AssertionError,
    strict=True,
    reason="Migration for lower(email) unique index not yet implemented (Phase 2 Task 15)"
)
def test_messy_legacy_data_duplicate_emails():
    """
    Calls real 'alembic upgrade head' on legacy database containing duplicate-case emails.
    Must fail or resolve per Phase 2 Task 15 migration once implemented.
    """
    if not is_postgres:
        pytest.skip("Requires PostgreSQL database for full migration validation")

    schema_name = "test_pg_messy_emails"
    pg_target_url = get_postgres_url_with_schema(schema_name)
    engine = create_engine(raw_url)

    with engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;"))
        conn.execute(text(f"CREATE SCHEMA {schema_name};"))
        conn.execute(text(f"""
            CREATE TABLE {schema_name}.alembic_version (version_num VARCHAR(32) PRIMARY KEY);
            INSERT INTO {schema_name}.alembic_version VALUES ('002_employer_user_id');

            CREATE TABLE {schema_name}.users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                role VARCHAR(32) NOT NULL
            );
            INSERT INTO {schema_name}.users (id, email, hashed_password, role)
            VALUES (1, 'User@Example.com', 'hash', 'student'),
                   (2, 'user@example.com', 'hash', 'student');
        """))

    try:
        run_alembic_upgrade(pg_target_url, "head")
        with engine.connect() as conn:
            dups = conn.execute(text(f"""
                SELECT lower(email) FROM {schema_name}.users GROUP BY lower(email) HAVING count(*) > 1
            """)).fetchall()
            assert len(dups) == 0, f"Duplicate lowercased emails remain: {dups}"
    finally:
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;"))


@pytest.mark.xfail(
    raises=AssertionError,
    strict=True,
    reason="Migration for role lowercase normalization not yet implemented (Phase 1 Task 8)"
)
def test_messy_legacy_data_mixed_case_roles():
    """
    Calls real 'alembic upgrade head' on legacy database containing mixed-case roles.
    Must normalize roles per Phase 1 Task 8 migration once implemented.
    """
    if not is_postgres:
        pytest.skip("Requires PostgreSQL database for full migration validation")

    schema_name = "test_pg_messy_roles"
    pg_target_url = get_postgres_url_with_schema(schema_name)
    engine = create_engine(raw_url)

    with engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;"))
        conn.execute(text(f"CREATE SCHEMA {schema_name};"))
        conn.execute(text(f"""
            CREATE TABLE {schema_name}.alembic_version (version_num VARCHAR(32) PRIMARY KEY);
            INSERT INTO {schema_name}.alembic_version VALUES ('002_employer_user_id');

            CREATE TABLE {schema_name}.users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                role VARCHAR(32) NOT NULL
            );
            INSERT INTO {schema_name}.users (id, email, hashed_password, role)
            VALUES (1, 's1@worknexus.io', 'hash', 'Student'),
                   (2, 'e1@worknexus.io', 'hash', 'EMPLOYER');
        """))

    try:
        run_alembic_upgrade(pg_target_url, "head")
        with engine.connect() as conn:
            invalid = conn.execute(text(f"""
                SELECT role FROM {schema_name}.users WHERE role NOT IN ('student', 'employer', 'institute', 'trainer', 'admin')
            """)).fetchall()
            assert len(invalid) == 0, f"Found unnormalized mixed-case roles: {invalid}"
    finally:
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;"))


@pytest.mark.xfail(
    raises=AssertionError,
    strict=True,
    reason="Migration for job_skills.skill_id integer FK not yet implemented (Phase 3 Task 19)"
)
def test_messy_legacy_data_string_vs_int_skill_ids():
    """
    Calls real 'alembic upgrade head' on legacy database containing string skill IDs in job_skills.
    Must convert or validate FK mapping per Phase 3 Task 19 migration once implemented.
    """
    if not is_postgres:
        pytest.skip("Requires PostgreSQL database for full migration validation")

    schema_name = "test_pg_messy_skills"
    pg_target_url = get_postgres_url_with_schema(schema_name)
    engine = create_engine(raw_url)

    with engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;"))
        conn.execute(text(f"CREATE SCHEMA {schema_name};"))
        conn.execute(text(f"""
            CREATE TABLE {schema_name}.alembic_version (version_num VARCHAR(32) PRIMARY KEY);
            INSERT INTO {schema_name}.alembic_version VALUES ('002_employer_user_id');

            CREATE TABLE {schema_name}.job_skills (
                id SERIAL PRIMARY KEY,
                job_id INTEGER NOT NULL,
                skill_id VARCHAR(64) NOT NULL
            );
            INSERT INTO {schema_name}.job_skills (id, job_id, skill_id)
            VALUES (1, 1, 'SK_PYTHON'), (2, 1, 'SK_SQL');
        """))

    try:
        run_alembic_upgrade(pg_target_url, "head")
        with engine.connect() as conn:
            col_type = conn.execute(text(f"""
                SELECT data_type FROM information_schema.columns 
                WHERE table_schema = '{schema_name}' AND table_name = 'job_skills' AND column_name = 'skill_id'
            """)).scalar()
            assert col_type in ('integer', 'smallint', 'bigint'), f"skill_id is {col_type}, not integer FK"
    finally:
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;"))
