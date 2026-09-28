"""create employer_feedback and employer_feedback_signals tables and align job_postings schema

Revision ID: 006_employer_feedback
Revises: 005_job_skills_int_fk
Create Date: 2026-09-28 23:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '006_employer_feedback'
down_revision: Union[str, Sequence[str], None] = '005_job_skills_int_fk'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Ensure job_postings.employer_id exists
    if 'job_postings' in tables:
        cols = [c['name'] for c in inspector.get_columns('job_postings')]
        if 'employer_id' not in cols:
            op.add_column('job_postings', sa.Column('employer_id', sa.Integer(), nullable=True))
            if 'employers' in tables:
                op.create_foreign_key(
                    'fk_job_postings_employer_id_employers',
                    'job_postings', 'employers',
                    ['employer_id'], ['id'],
                    ondelete='SET NULL'
                )
            op.create_index('ix_job_postings_employer_id', 'job_postings', ['employer_id'])

    # 2. Create employer_feedback table if it doesn't exist
    if 'employer_feedback' not in tables:
        op.create_table(
            'employer_feedback',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column('employer_id', sa.Integer(), sa.ForeignKey('employers.id', ondelete='CASCADE'), nullable=False),
            sa.Column('course_id', sa.Integer(), sa.ForeignKey('courses.id', ondelete='SET NULL'), nullable=True),
            sa.Column('comments', sa.Text(), nullable=False),
            sa.Column('rating', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_employer_feedback_id', 'employer_feedback', ['id'])
        op.create_index('ix_employer_feedback_employer_id', 'employer_feedback', ['employer_id'])
        op.create_index('ix_employer_feedback_course_id', 'employer_feedback', ['course_id'])

    # 3. Create employer_feedback_signals table if it doesn't exist
    if 'employer_feedback_signals' not in tables:
        op.create_table(
            'employer_feedback_signals',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column('feedback_id', sa.Integer(), sa.ForeignKey('employer_feedback.id', ondelete='CASCADE'), nullable=False),
            sa.Column('skill_id', sa.String(length=50), nullable=False),
            sa.Column('confidence_score', sa.Float(), nullable=False, server_default='0.95'),
            sa.Column('trust_weight', sa.Float(), nullable=False, server_default='1.0'),
            sa.Column('weighted_signal', sa.Float(), nullable=False, server_default='0.95'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_employer_feedback_signals_id', 'employer_feedback_signals', ['id'])
        op.create_index('ix_employer_feedback_signals_feedback_id', 'employer_feedback_signals', ['feedback_id'])
        op.create_index('ix_employer_feedback_signals_skill_id', 'employer_feedback_signals', ['skill_id'])
    else:
        # Reconcile existing employer_feedback_signals if skill_id holds string codes that need mapping
        if 'skills' in tables and conn.dialect.name == "postgresql":
            skills_cols = [c['name'] for c in inspector.get_columns('skills')]
            if 'skill_id' in skills_cols:
                conn.execute(text("""
                    UPDATE employer_feedback_signals s
                    SET skill_id = CAST(sk.id AS text)
                    FROM skills sk
                    WHERE s.skill_id = sk.skill_id;
                """))
            conn.execute(text("""
                DELETE FROM employer_feedback_signals
                WHERE CAST(skill_id AS text) NOT IN (SELECT CAST(id AS text) FROM skills);
            """))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'employer_feedback_signals' in tables:
        op.drop_index('ix_employer_feedback_signals_skill_id', table_name='employer_feedback_signals')
        op.drop_index('ix_employer_feedback_signals_feedback_id', table_name='employer_feedback_signals')
        op.drop_index('ix_employer_feedback_signals_id', table_name='employer_feedback_signals')
        op.drop_table('employer_feedback_signals')

    if 'employer_feedback' in tables:
        op.drop_index('ix_employer_feedback_course_id', table_name='employer_feedback')
        op.drop_index('ix_employer_feedback_employer_id', table_name='employer_feedback')
        op.drop_index('ix_employer_feedback_id', table_name='employer_feedback')
        op.drop_table('employer_feedback')

    if 'job_postings' in tables:
        cols = [c['name'] for c in inspector.get_columns('job_postings')]
        if 'employer_id' in cols:
            op.drop_index('ix_job_postings_employer_id', table_name='job_postings')
            op.drop_constraint('fk_job_postings_employer_id_employers', 'job_postings', type_='foreignkey')
            op.drop_column('job_postings', 'employer_id')
