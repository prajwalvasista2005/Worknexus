"""add status and is_verified columns to student_skill_evidence

Revision ID: 007_evidence_status_verified
Revises: 006_employer_feedback
Create Date: 2026-09-30 12:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '007_evidence_status_verified'
down_revision: Union[str, Sequence[str], None] = '006_employer_feedback'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'student_skill_evidence' in tables:
        cols = [c['name'] for c in inspector.get_columns('student_skill_evidence')]
        if 'status' not in cols:
            op.add_column(
                'student_skill_evidence',
                sa.Column('status', sa.String(length=32), nullable=True, server_default='verified')
            )
        if 'is_verified' not in cols:
            op.add_column(
                'student_skill_evidence',
                sa.Column('is_verified', sa.Boolean(), nullable=True, server_default=sa.true())
            )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'student_skill_evidence' in tables:
        cols = [c['name'] for c in inspector.get_columns('student_skill_evidence')]
        if 'is_verified' in cols:
            op.drop_column('student_skill_evidence', 'is_verified')
        if 'status' in cols:
            op.drop_column('student_skill_evidence', 'status')
