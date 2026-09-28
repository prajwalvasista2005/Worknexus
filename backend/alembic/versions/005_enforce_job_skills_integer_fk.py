"""enforce job_skills skill_id as integer foreign key referencing skills.id with cascade

Revision ID: 005_job_skills_int_fk
Revises: 004_normalize_roles
Create Date: 2026-09-28 23:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '005_job_skills_int_fk'
down_revision: Union[str, Sequence[str], None] = '004_normalize_roles'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'job_skills' in tables and 'skills' in tables:
        skills_cols = [c['name'] for c in inspector.get_columns('skills')]

        if conn.dialect.name == "postgresql":
            # 1. Map string codes to skills.id if skills table has skill_id column
            if 'skill_id' in skills_cols:
                conn.execute(text("""
                    UPDATE job_skills js
                    SET skill_id = CAST(s.id AS text)
                    FROM skills s
                    WHERE CAST(js.skill_id AS text) = s.skill_id;
                """))

            # 2. Delete orphaned records that cannot be mapped to existing skills.id
            conn.execute(text("""
                DELETE FROM job_skills
                WHERE CAST(skill_id AS text) !~ '^[0-9]+$'
                   OR CAST(skill_id AS integer) NOT IN (SELECT id FROM skills);
            """))

            # 3. Delete orphaned records where job_id does not exist in job_postings (if job_postings exists)
            if 'job_postings' in tables:
                conn.execute(text("""
                    DELETE FROM job_skills
                    WHERE job_id NOT IN (SELECT id FROM job_postings);
                """))

            # 4. Drop existing foreign key constraints on job_skills if present
            fks = inspector.get_foreign_keys('job_skills')
            for fk in fks:
                if 'skill_id' in fk.get('constrained_columns', []):
                    op.drop_constraint(fk['name'], 'job_skills', type_='foreignkey')

            # 5. Alter column type to INTEGER
            conn.execute(text("""
                ALTER TABLE job_skills
                ALTER COLUMN skill_id TYPE INTEGER USING skill_id::integer;
            """))

            # 6. Add foreign key constraint referencing skills(id) ON DELETE CASCADE
            conn.execute(text("""
                ALTER TABLE job_skills
                ADD CONSTRAINT fk_job_skills_skill_id
                FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE;
            """))

            # 7. Ensure foreign key on job_id referencing job_postings(id) ON DELETE CASCADE
            has_job_fk = any('job_id' in fk.get('constrained_columns', []) for fk in fks)
            if not has_job_fk and 'job_postings' in tables:
                conn.execute(text("""
                    ALTER TABLE job_skills
                    ADD CONSTRAINT fk_job_skills_job_id
                    FOREIGN KEY (job_id) REFERENCES job_postings(id) ON DELETE CASCADE;
                """))
        else:
            # SQLite / Generic
            pass


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'job_skills' in tables:
        if conn.dialect.name == "postgresql":
            conn.execute(text("ALTER TABLE job_skills DROP CONSTRAINT IF EXISTS fk_job_skills_skill_id;"))
            conn.execute(text("ALTER TABLE job_skills ALTER COLUMN skill_id TYPE VARCHAR(50) USING skill_id::varchar;"))
            # Optionally re-add reference to skills.skill_id
            if 'skills' in tables:
                columns = [c['name'] for c in inspector.get_columns('skills')]
                if 'skill_id' in columns:
                    conn.execute(text("""
                        ALTER TABLE job_skills
                        ADD CONSTRAINT job_skills_skill_id_fkey
                        FOREIGN KEY (skill_id) REFERENCES skills(skill_id);
                    """))
