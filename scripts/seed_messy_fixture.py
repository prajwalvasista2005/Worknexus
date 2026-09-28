#!/usr/bin/env python3
"""
scripts/seed_messy_fixture.py
Seeds a target PostgreSQL database with legacy data up to migration 001_phase10,
including unambiguous employer-user pairs ready for migration 002 verification.
"""
import os
import sys
from sqlalchemy import create_engine, text

def seed_messy_fixture():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        user = os.getenv("POSTGRES_USER", "postgres")
        pw = os.getenv("POSTGRES_PASSWORD", "postgres")
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "SkillSync")
        db_url = f"postgresql://{user}:{pw}@{host}:{port}/{db}"

    print(f"==> Connecting to {db_url.split('@')[-1]} to seed messy legacy fixture...")
    engine = create_engine(db_url)

    with engine.begin() as conn:
        # Create core tables as they existed at 001_phase10
        conn.execute(text("""
            DROP TABLE IF EXISTS employers CASCADE;
            DROP TABLE IF EXISTS users CASCADE;
            DROP TABLE IF EXISTS skills CASCADE;
            DROP TABLE IF EXISTS job_postings CASCADE;
            DROP TABLE IF EXISTS job_skills CASCADE;
            DROP TABLE IF EXISTS alembic_version CASCADE;

            CREATE TABLE alembic_version (
                version_num VARCHAR(32) NOT NULL PRIMARY KEY
            );
            INSERT INTO alembic_version (version_num) VALUES ('001_phase10');

            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) NOT NULL UNIQUE,
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

        # Seed valid users and matching employers (unambiguous)
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

        # Reset sequences
        conn.execute(text("""
            SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));
            SELECT setval('employers_id_seq', (SELECT MAX(id) FROM employers));
            SELECT setval('skills_id_seq', (SELECT MAX(id) FROM skills));
        """))

    print("==> Messy legacy fixture successfully seeded!")

if __name__ == "__main__":
    seed_messy_fixture()
