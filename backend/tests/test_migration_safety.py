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
                with conn.begin_nested():
                    conn.execute(text(f"""
                        INSERT INTO {schema_name}.employers (id, user_id, company_name)
                        VALUES (2, 10, 'Duplicate Employer User')
                    """))

            # 3. Assert PostgreSQL FOREIGN KEY constraint referencing users(id)
            with pytest.raises(IntegrityError):
                with conn.begin_nested():
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

def test_messy_legacy_data_duplicate_emails():
    """
    Calls real 'alembic upgrade head' on legacy database containing duplicate-case emails,
    verifies migration 003 reconciles duplicates and enforces case-insensitive unique constraint.
    PostgreSQL itself must reject duplicate lowercased emails at the database level with IntegrityError.
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

        # Verify deduplication occurred and email is normalized
        with engine.connect() as conn:
            users = conn.execute(text(f"SELECT id, email FROM {schema_name}.users ORDER BY id")).fetchall()
            assert len(users) == 1
            assert users[0][1] == "user@example.com"

        # Attempting to insert a duplicate case-insensitive email must fail with IntegrityError
        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                conn.execute(text(f"""
                    INSERT INTO {schema_name}.users (email, hashed_password, role)
                    VALUES ('USER@EXAMPLE.COM', 'hash2', 'student');
                """))
    finally:
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;"))


def test_messy_legacy_data_mixed_case_roles():
    """
    Calls real 'alembic upgrade head' on legacy database containing mixed-case roles,
    verifies migration 004 normalizes legacy roles to canonical lowercase and applies check constraint.
    PostgreSQL itself must reject unnormalized or invalid values with IntegrityError.
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

        # Verify roles are normalized to canonical lowercase
        with engine.connect() as conn:
            roles = conn.execute(text(f"SELECT id, role FROM {schema_name}.users ORDER BY id")).fetchall()
            assert roles[0][1] == "student"
            assert roles[1][1] == "employer"

        # Verify check constraint rejects invalid or unnormalized role
        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                conn.execute(text(f"""
                    INSERT INTO {schema_name}.users (email, hashed_password, role)
                    VALUES ('invalid@worknexus.io', 'hash3', 'INVALID_ROLE');
                """))
    finally:
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;"))


@pytest.mark.xfail(
    raises=IntegrityError,
    strict=True,
    reason="Attempting to enforce integer foreign key constraint on orphaned skill_id must fail with IntegrityError at DB level until Phase 3 Task 19 migration standardizes skill keys"
)
def test_messy_legacy_data_string_vs_int_skill_ids():
    """
    Calls real 'alembic upgrade head' on legacy database containing orphaned skill IDs,
    then attempts to enforce the foreign key constraint referencing skills(id).
    PostgreSQL itself must reject orphaned foreign keys with IntegrityError.
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

            CREATE TABLE {schema_name}.skills (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                category VARCHAR(64) NOT NULL
            );
            INSERT INTO {schema_name}.skills (id, name, category)
            VALUES (1, 'Python', 'Backend'), (2, 'SQL', 'Database');

            CREATE TABLE {schema_name}.job_skills (
                id SERIAL PRIMARY KEY,
                job_id INTEGER NOT NULL,
                skill_id INTEGER NOT NULL
            );
            INSERT INTO {schema_name}.job_skills (id, job_id, skill_id)
            VALUES (1, 1, 1), (2, 1, 999999);
        """))

    try:
        run_alembic_upgrade(pg_target_url, "head")
        # Attempt to enforce the foreign key constraint referencing skills(id)
        with engine.begin() as conn:
            conn.execute(text(f"""
                ALTER TABLE {schema_name}.job_skills
                ADD CONSTRAINT fk_job_skills_skill_id
                FOREIGN KEY (skill_id) REFERENCES {schema_name}.skills(id);
            """))
    finally:
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;"))
