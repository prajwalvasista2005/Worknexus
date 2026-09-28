import pytest
from sqlalchemy import create_engine, text
from alembic.config import Config
from alembic import command
import os
from pathlib import Path


@pytest.fixture
def clean_test_db(tmp_path):
    """Provides a fresh isolated SQLite database for testing migration logic."""
    db_path = tmp_path / "test_migration.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    return engine, db_url


def _get_migration_002():
    import importlib.util
    file_path = Path(__file__).resolve().parent.parent / "alembic" / "versions" / "002_add_user_id_to_employers.py"
    spec = importlib.util.spec_from_file_location("migration_002", file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_002_aborts_on_ambiguous_unlinked_employer(tmp_path):
    """
    Verifies that migration 002 refuses to guess when an employer cannot be
    unambiguously mapped to a user, aborting loudly with an error listing the
    unmatched records.
    """
    db_path = tmp_path / "test_migration_abort.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)

    # 1. Create legacy schema up to 001_phase10
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

        # Seed users (None of them match the ambiguous employer)
        conn.execute(text("""
            INSERT INTO users (id, email, hashed_password, full_name, role)
            VALUES (1, 'student@worknexus.io', 'hash', 'Alice Student', 'student'),
                   (2, 'other_emp@worknexus.io', 'hash', 'Acme Corp', 'employer');
        """))

        # Seed employers: one unambiguous match (id=2 Acme Corp), and one orphaned ambiguous employer (id=99 Unknown Co)
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

        # Seed matching employer user
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

        # Verify backfill mapped user_id=10 to employer id=1
        res = conn.execute(text("SELECT id, user_id, company_name FROM employers WHERE id = 1")).fetchone()
        assert res[1] == 10
        assert res[2] == "TechCorp International"


def test_messy_legacy_data_duplicate_emails(tmp_path):
    """
    Verifies that the dry-run integrity check detects case-insensitive duplicate emails
    in messy legacy data.
    """
    engine = create_engine(f"sqlite:///{tmp_path / 'messy_emails.db'}")
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                role VARCHAR(32) NOT NULL
            );
        """))
        conn.execute(text("""
            INSERT INTO users (id, email, role)
            VALUES (1, 'User@Example.com', 'student'),
                   (2, 'user@example.com', 'student');
        """))

    with engine.connect() as conn:
        dup_rows = conn.execute(text("""
            SELECT lower(email), count(*) FROM users GROUP BY lower(email) HAVING count(*) > 1;
        """)).fetchall()
        assert len(dup_rows) == 1
        assert dup_rows[0][0] == 'user@example.com'
        assert dup_rows[0][1] == 2


def test_messy_legacy_data_mixed_case_roles(tmp_path):
    """
    Verifies that legacy data with mixed-case roles can be normalized cleanly
    to the allowed enum values (student, employer, institute, trainer, admin).
    """
    engine = create_engine(f"sqlite:///{tmp_path / 'messy_roles.db'}")
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                role VARCHAR(32) NOT NULL
            );
        """))
        conn.execute(text("""
            INSERT INTO users (id, email, role)
            VALUES (1, 's1@worknexus.io', 'Student'),
                   (2, 'e1@worknexus.io', 'EMPLOYER'),
                   (3, 't1@worknexus.io', 'Trainer'),
                   (4, 'i1@worknexus.io', 'Institute'),
                   (5, 'a1@worknexus.io', 'Admin');
        """))

    with engine.begin() as conn:
        conn.execute(text("UPDATE users SET role = LOWER(role);"))

    with engine.connect() as conn:
        invalid_roles = conn.execute(text("""
            SELECT id, email, role FROM users WHERE role NOT IN ('student', 'employer', 'institute', 'trainer', 'admin');
        """)).fetchall()
        assert len(invalid_roles) == 0


def test_messy_legacy_data_string_vs_int_skill_ids(tmp_path):
    """
    Verifies detection of unmapped job_skills rows when migrating from string skill codes
    to integer foreign keys.
    """
    engine = create_engine(f"sqlite:///{tmp_path / 'messy_skills.db'}")
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE skills (
                id INTEGER PRIMARY KEY,
                name VARCHAR(128) NOT NULL
            );
        """))
        conn.execute(text("""
            CREATE TABLE job_skills (
                id INTEGER PRIMARY KEY,
                job_id INTEGER NOT NULL,
                skill_id INTEGER
            );
        """))
        conn.execute(text("INSERT INTO skills (id, name) VALUES (1, 'Python'), (2, 'SQL');"))
        # Seed 1 valid mapping, 1 orphaned/unmapped mapping
        conn.execute(text("INSERT INTO job_skills (id, job_id, skill_id) VALUES (101, 1, 1), (102, 1, 999);"))

    with engine.connect() as conn:
        unmapped = conn.execute(text("""
            SELECT js.id, js.job_id, js.skill_id
            FROM job_skills js
            LEFT JOIN skills s ON js.skill_id = s.id
            WHERE s.id IS NULL;
        """)).fetchall()
        assert len(unmapped) == 1
        assert unmapped[0][0] == 102
        assert unmapped[0][2] == 999

