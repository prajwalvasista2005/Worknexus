"""add user_id to employers table

Revision ID: 002_employer_user_id
Revises: 001_phase10
Create Date: 2026-09-26 23:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_employer_user_id'
down_revision: Union[str, Sequence[str], None] = '001_phase10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user_id foreign key column to employers table."""
    conn = op.get_bind()
    # Check if table exists (for environments where employers was created by Base.metadata.create_all)
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if 'employers' in tables:
        columns = [c['name'] for c in inspector.get_columns('employers')]
        if 'user_id' not in columns:
            op.add_column('employers', sa.Column('user_id', sa.Integer(), nullable=True))
            op.create_foreign_key(
                'fk_employers_user_id_users',
                'employers', 'users',
                ['user_id'], ['id'],
                ondelete='CASCADE'
            )
            op.create_index('ix_employers_user_id', 'employers', ['user_id'], unique=True)
    else:
        op.create_table(
            'employers',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True, unique=True),
            sa.Column('company_name', sa.String(length=255), nullable=False),
            sa.Column('trust_weight', sa.Float(), nullable=False, server_default='1.0'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_employers_id', 'employers', ['id'])
        op.create_index('ix_employers_user_id', 'employers', ['user_id'], unique=True)
        op.create_index('ix_employers_company_name', 'employers', ['company_name'])


def downgrade() -> None:
    """Revert user_id from employers table."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if 'employers' in tables:
        columns = [c['name'] for c in inspector.get_columns('employers')]
        if 'user_id' in columns:
            op.drop_index('ix_employers_user_id', table_name='employers')
            op.drop_constraint('fk_employers_user_id_users', 'employers', type_='foreignkey')
            op.drop_column('employers', 'user_id')
