#!/usr/bin/env python3
"""
scripts/seed_messy_fixture.py
Seeds a target PostgreSQL database with legacy raw SQL schema at pre-002 state (001_phase10).
Never uses Base.metadata.create_all.

Usage:
    python scripts/seed_messy_fixture.py --messy   # Seeds known-bad data tripping dry-run integrity checks
    python scripts/seed_messy_fixture.py --clean   # Seeds unambiguous, valid data where dry-run passes green
"""
import os
import sys
import argparse
import urllib.parse
from pathlib import Path
from sqlalchemy import create_engine, text


def get_db_url():
    try:
        from dotenv import load_dotenv
        root_env = Path(__file__).resolve().parent.parent / ".env"
        backend_env = Path(__file__).resolve().parent.parent / "backend" / ".env"
        if root_env.exists():
            load_dotenv(root_env)
        elif backend_env.exists():
            load_dotenv(backend_env)
    except ImportError:
        pass

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        user = os.getenv("POSTGRES_USER", os.getenv("DB_USER", "postgres"))
        pw = os.getenv("POSTGRES_PASSWORD", os.getenv("DB_PASSWORD", "postgres"))
        encoded_pw = urllib.parse.quote(pw, safe="")
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        db = os.getenv("POSTGRES_DB", os.getenv("DB_NAME", "SkillSync"))
        db_url = f"postgresql://{user}:{encoded_pw}@{host}:{port}/{db}"
    return db_url


def seed_fixture(mode: str = "messy"):
    db_url = get_db_url()
    print(f"==> Connecting to database to seed [{mode.upper()}] legacy fixture...")
    engine = create_engine(db_url)

    with engine.begin() as conn:
        # Create core tables using RAW SQL at pre-002 state (never create_all)
        conn.execute(text("""
            DROP TABLE IF EXISTS employer_feedback_signals CASCADE;
            DROP TABLE IF EXISTS employer_feedback CASCADE;
            DROP TABLE IF EXISTS refresh_tokens CASCADE;
            DROP TABLE IF EXISTS user_skills CASCADE;
            DROP TABLE IF EXISTS course_skills CASCADE;
            DROP TABLE IF EXISTS courses CASCADE;
            DROP TABLE IF EXISTS student_skill_evidence CASCADE;
            DROP TABLE IF EXISTS student_profiles CASCADE;
            DROP TABLE IF EXISTS role_skills CASCADE;
            DROP TABLE IF EXISTS target_roles CASCADE;
            DROP TABLE IF EXISTS employers CASCADE;
            DROP TABLE IF EXISTS users CASCADE;
            DROP TABLE IF EXISTS skills CASCADE;
            DROP TABLE IF EXISTS job_postings CASCADE;
            DROP TABLE IF EXISTS job_skills CASCADE;
            DROP TABLE IF EXISTS alembic_version CASCADE;

            -- Stamp version at 001_phase10 (pre-002 revision)
            CREATE TABLE alembic_version (
                version_num VARCHAR(32) NOT NULL PRIMARY KEY
            );
            INSERT INTO alembic_version (version_num) VALUES ('001_phase10');

            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                role VARCHAR(32) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            CREATE TABLE employers (
                id SERIAL PRIMARY KEY,
                company_name VARCHAR(255) NOT NULL,
                trust_weight FLOAT NOT NULL DEFAULT 1.0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            CREATE TABLE skills (
                id SERIAL PRIMARY KEY,
                name VARCHAR(128) NOT NULL UNIQUE,
                category VARCHAR(64) NOT NULL
            );

            CREATE TABLE job_postings (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            CREATE TABLE job_skills (
                id SERIAL PRIMARY KEY,
                job_id INTEGER NOT NULL,
                skill_id INTEGER NOT NULL
            );
        """))

        if mode == "messy":
            print("==> Seeding deliberately messy legacy data that trips integrity checks...")
            # 1. Duplicate-case emails: 'student@worknexus.io' and 'Student@worknexus.io'
            # 2. Mixed-case and invalid roles: 'Student', 'EMPLOYER', 'SuperAdmin'
            # 3. Unlinked ambiguous employer: id=99 'Orphaned Mystery Corp' (trips migration 002 abort)
            # 4. Unmapped job_skill: references non-existent skill id 9999
            conn.execute(text("""
                INSERT INTO users (id, email, hashed_password, full_name, role)
                VALUES
                    (1, 'emp_one@worknexus.io', 'hash123', 'Acme Corporation', 'EMPLOYER'),
                    (2, 'student@worknexus.io', 'hash123', 'Alice Student', 'Student'),
                    (3, 'Student@worknexus.io', 'hash123', 'Alice Duplicate Case', 'student'),
                    (4, 'invalid_role@worknexus.io', 'hash123', 'Bob Invalid', 'SuperAdmin');

                INSERT INTO employers (id, company_name)
                VALUES
                    (1, 'Acme Corporation'),
                    (99, 'Orphaned Mystery Corp');

                INSERT INTO skills (id, name, category)
                VALUES (1, 'Python', 'Backend'), (2, 'SQL', 'Database');

                INSERT INTO job_postings (id, title)
                VALUES (1, 'Software Engineer');

                INSERT INTO job_skills (id, job_id, skill_id)
                VALUES (1, 1, 1), (2, 1, 9999);
            """))
        else:
            print("==> Seeding clean unambiguous legacy data where dry-run passes green...")
            conn.execute(text("""
                INSERT INTO users (id, email, hashed_password, full_name, role)
                VALUES
                    (1, 'emp_one@worknexus.io', 'hash123', 'Acme Corporation', 'employer'),
                    (2, 'emp_two@worknexus.io', 'hash123', 'Global Logistics', 'employer'),
                    (3, 'student@worknexus.io', 'hash123', 'Student Alice', 'student');

                INSERT INTO employers (id, company_name)
                VALUES
                    (1, 'Acme Corporation'),
                    (2, 'Global Logistics');

                INSERT INTO skills (id, name, category)
                VALUES (1, 'Python', 'Backend'), (2, 'SQL', 'Database');

                INSERT INTO job_postings (id, title)
                VALUES (1, 'Software Engineer');

                INSERT INTO job_skills (id, job_id, skill_id)
                VALUES (1, 1, 1), (2, 1, 2);
            """))

        conn.execute(text("""
            SELECT setval('users_id_seq', (SELECT COALESCE(MAX(id), 1) FROM users));
            SELECT setval('employers_id_seq', (SELECT COALESCE(MAX(id), 1) FROM employers));
            SELECT setval('skills_id_seq', (SELECT COALESCE(MAX(id), 1) FROM skills));
        """))

    print(f"==> [{mode.upper()}] legacy fixture successfully seeded!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed PostgreSQL legacy fixture for migration testing")
    parser.add_argument("--clean", action="store_true", help="Seed clean unambiguous data (dry-run passes green)")
    parser.add_argument("--messy", action="store_true", help="Seed messy data tripping integrity checks (default)")
    args = parser.parse_args()

    mode = "clean" if args.clean else "messy"
    seed_fixture(mode=mode)
