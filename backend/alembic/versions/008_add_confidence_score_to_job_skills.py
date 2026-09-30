"""add confidence_score to job_skills

This migration closes the schema drift between the JobSkill ORM model
(which declares `confidence_score: Mapped[float]`) and the actual
`job_skills` table in PostgreSQL (which was created without that column).

Without this column any query that touches JobSkill.confidence_score —
including `db.query(JobSkill).all()` issued by MLDataService.get_live_jobs_data()
— raises:
    psycopg2.errors.UndefinedColumn: column job_skills.confidence_score does not exist

That error, when swallowed by a bare `except Exception: pass` block, leaves the
PostgreSQL connection in `InFailedSqlTransaction` state, poisoning every
subsequent query in the same request lifecycle.

Revision ID: 008_job_skills_confidence
Revises: 007_evidence_status_verified
Create Date: 2026-09-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '008_job_skills_confidence'
down_revision: Union[str, Sequence[str], None] = '007_evidence_status_verified'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'job_skills' in tables:
        existing_cols = [c['name'] for c in inspector.get_columns('job_skills')]
        if 'confidence_score' not in existing_cols:
            op.add_column(
                'job_skills',
                sa.Column(
                    'confidence_score',
                    sa.Float(),
                    nullable=True,
                    server_default='1.0',
                )
            )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'job_skills' in tables:
        existing_cols = [c['name'] for c in inspector.get_columns('job_skills')]
        if 'confidence_score' in existing_cols:
            op.drop_column('job_skills', 'confidence_score')
