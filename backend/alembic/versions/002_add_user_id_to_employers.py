"""add user_id to employers table with backfill and foreign key constraint

Revision ID: 002_employer_user_id
Revises: 001_phase10
Create Date: 2026-09-26 23:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '002_employer_user_id'
down_revision: Union[str, Sequence[str], None] = '001_phase10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user_id foreign key column to employers table, backfill profiles, and enforce constraints."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'employers' in tables:
        columns = [c['name'] for c in inspector.get_columns('employers')]
        if 'user_id' not in columns:
            op.add_column('employers', sa.Column('user_id', sa.Integer(), nullable=True))

        # 1. Backfill existing employers where user_id is NULL
        # Match by id if user is an employer
        conn.execute(text("""
            UPDATE employers
            SET user_id = employers.id
            WHERE employers.user_id IS NULL
              AND EXISTS (
                  SELECT 1 FROM users
                  WHERE users.id = employers.id
                    AND LOWER(users.role) = 'employer'
              );
        """))

        # Match by company_name == users.full_name
        conn.execute(text("""
            UPDATE employers
            SET user_id = users.id
            FROM users
            WHERE employers.user_id IS NULL
              AND LOWER(users.role) = 'employer'
              AND users.full_name IS NOT NULL
              AND LOWER(TRIM(users.full_name)) = LOWER(TRIM(employers.company_name))
              AND NOT EXISTS (
                  SELECT 1 FROM employers e2 WHERE e2.user_id = users.id
              );
        """))

        # Link any remaining unlinked employer to an unprofiled employer user
        unlinked_emp_rows = conn.execute(text("SELECT id FROM employers WHERE user_id IS NULL ORDER BY id")).fetchall()
        unprofiled_users = conn.execute(text("""
            SELECT id, full_name FROM users
            WHERE LOWER(role) = 'employer'
              AND NOT EXISTS (SELECT 1 FROM employers WHERE employers.user_id = users.id)
            ORDER BY id
        """)).fetchall()

        idx = 0
        while idx < len(unlinked_emp_rows) and idx < len(unprofiled_users):
            emp_row_id = unlinked_emp_rows[idx][0]
            u_id = unprofiled_users[idx][0]
            u_name = unprofiled_users[idx][1]
            conn.execute(text("""
                UPDATE employers
                SET user_id = :u_id,
                    company_name = CASE WHEN company_name IN ('Test Employer', 'Enterprise Partner') AND :u_name IS NOT NULL THEN :u_name ELSE company_name END
                WHERE id = :emp_id
            """), {"u_id": u_id, "u_name": u_name, "emp_id": emp_row_id})
            idx += 1

        # 2. Provision new employer records for any remaining employer users who still lack one
        remaining_users = unprofiled_users[idx:]
        for u_id, u_name in remaining_users:
            cname = u_name or "Enterprise Partner"
            conn.execute(text("""
                INSERT INTO employers (user_id, company_name, trust_weight, created_at)
                VALUES (:u_id, :cname, 1.0, NOW());
            """), {"u_id": u_id, "cname": cname})

        # 3. Add UNIQUE constraint and index on user_id
        # First ensure unique index
        indexes = [i['name'] for i in inspector.get_indexes('employers')]
        if 'ix_employers_user_id' not in indexes:
            op.create_index('ix_employers_user_id', 'employers', ['user_id'], unique=True)

        # 4. Add FOREIGN KEY constraint to users(id) ON DELETE CASCADE
        fks = [fk['name'] for fk in inspector.get_foreign_keys('employers')]
        if 'fk_employers_user_id_users' not in fks:
            op.create_foreign_key(
                'fk_employers_user_id_users',
                'employers', 'users',
                ['user_id'], ['id'],
                ondelete='CASCADE'
            )
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
            op.drop_constraint('fk_employers_user_id_users', 'employers', type_='foreignkey')
            op.drop_index('ix_employers_user_id', table_name='employers')
            op.drop_column('employers', 'user_id')
