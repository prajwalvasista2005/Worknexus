"""add trainer_interventions table

Phase 1 — Loop D implementation.

Creates the `trainer_interventions` table with all columns, indexes, and
foreign key constraints needed by TrainerIntervention ORM model.

Revision ID: 009_trainer_interventions
Revises: 008_job_skills_confidence
Create Date: 2026-10-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '009_trainer_interventions'
down_revision: Union[str, Sequence[str], None] = '008_job_skills_confidence'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'trainer_interventions' not in tables:
        op.create_table(
            'trainer_interventions',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('trainer_id', sa.Integer(), nullable=False),
            sa.Column('student_id', sa.Integer(), nullable=False),
            sa.Column('skill_id', sa.Integer(), nullable=False),
            sa.Column('intervention_type', sa.String(length=64), nullable=False, server_default='coaching'),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('proficiency_before', sa.String(length=32), nullable=True),
            sa.Column('proficiency_after', sa.String(length=32), nullable=True),
            sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column(
                'created_at',
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text('now()'),
            ),
            # Primary key
            sa.PrimaryKeyConstraint('id'),
            # Foreign keys
            sa.ForeignKeyConstraint(
                ['trainer_id'],
                ['users.id'],
                ondelete='CASCADE',
                name='fk_ti_trainer_id',
            ),
            sa.ForeignKeyConstraint(
                ['student_id'],
                ['users.id'],
                ondelete='CASCADE',
                name='fk_ti_student_id',
            ),
            sa.ForeignKeyConstraint(
                ['skill_id'],
                ['skills.id'],
                ondelete='CASCADE',
                name='fk_ti_skill_id',
            ),
        )

        # Indexes for common lookup patterns
        op.create_index('ix_ti_trainer_id', 'trainer_interventions', ['trainer_id'])
        op.create_index('ix_ti_student_id', 'trainer_interventions', ['student_id'])
        op.create_index('ix_ti_skill_id', 'trainer_interventions', ['skill_id'])
        op.create_index('ix_ti_created_at', 'trainer_interventions', ['created_at'])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'trainer_interventions' in tables:
        op.drop_index('ix_ti_created_at', table_name='trainer_interventions')
        op.drop_index('ix_ti_skill_id', table_name='trainer_interventions')
        op.drop_index('ix_ti_student_id', table_name='trainer_interventions')
        op.drop_index('ix_ti_trainer_id', table_name='trainer_interventions')
        op.drop_table('trainer_interventions')
