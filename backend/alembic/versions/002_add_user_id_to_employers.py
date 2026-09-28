"""add user_id to employers table with safe unambiguous backfill and foreign key constraint

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
    """Add user_id foreign key column to employers table, backfill profiles safely, and enforce constraints."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'employers' in tables:
        columns = [c['name'] for c in inspector.get_columns('employers')]
        if 'user_id' not in columns:
            op.add_column('employers', sa.Column('user_id', sa.Integer(), nullable=True))

        # 1. Safe, unambiguous backfill step A:
        # Match by ID if and only if:
        # - users.id == employers.id
        # - users.role is 'employer'
        # - no other employer is already linked to users.id
        conn.execute(text("""
            UPDATE employers
            SET user_id = (
                SELECT users.id FROM users
                WHERE users.id = employers.id
                  AND LOWER(users.role) = 'employer'
                  AND NOT EXISTS (SELECT 1 FROM employers e2 WHERE e2.user_id = users.id)
            )
            WHERE employers.user_id IS NULL
              AND EXISTS (
                  SELECT 1 FROM users
                  WHERE users.id = employers.id
                    AND LOWER(users.role) = 'employer'
                    AND NOT EXISTS (SELECT 1 FROM employers e2 WHERE e2.user_id = users.id)
              );
        """))

        # 2. Safe, unambiguous backfill step B:
        # Match by company_name == users.full_name ONLY when there is an EXACT 1:1 match:
        # - Exactly one user with role 'employer' has full_name matching company_name
        # - Exactly one unlinked employer has this company_name
        # - The user is not already linked to any employer
        conn.execute(text("""
            WITH unique_users AS (
                SELECT LOWER(TRIM(u.full_name)) AS norm_name, MIN(u.id) AS single_user_id
                FROM users u
                WHERE LOWER(u.role) = 'employer'
                  AND u.full_name IS NOT NULL
                  AND NOT EXISTS (SELECT 1 FROM employers e WHERE e.user_id = u.id)
                GROUP BY LOWER(TRIM(u.full_name))
                HAVING COUNT(*) = 1
            ),
            unique_employers AS (
                SELECT LOWER(TRIM(e.company_name)) AS norm_company, MIN(e.id) AS single_emp_id
                FROM employers e
                WHERE e.user_id IS NULL
                  AND e.company_name IS NOT NULL
                GROUP BY LOWER(TRIM(e.company_name))
                HAVING COUNT(*) = 1
            )
            UPDATE employers
            SET user_id = (
                SELECT uu.single_user_id
                FROM unique_users uu
                WHERE uu.norm_name = LOWER(TRIM(employers.company_name))
            )
            WHERE employers.user_id IS NULL
              AND EXISTS (
                  SELECT 1
                  FROM unique_employers ue
                  JOIN unique_users uu ON ue.norm_company = uu.norm_name
                  WHERE ue.single_emp_id = employers.id
              );
        """))

        # 3. SAFETY CHECK: Never guess.
        # If any employer record still has user_id IS NULL, abort with a loud error listing offending rows.
        unlinked = conn.execute(text(
            "SELECT id, company_name FROM employers WHERE user_id IS NULL ORDER BY id"
        )).fetchall()

        if unlinked:
            offending = [f"(id={row[0]}, company='{row[1]}')" for row in unlinked]
            raise RuntimeError(
                f"Migration 002 aborted: Found {len(unlinked)} unlinked employer record(s) without an "
                f"unambiguous user match: {', '.join(offending)}. Manual reconciliation required to "
                f"prevent incorrect account ownership assignment. Do not guess."
            )

        # 4. SAFETY CHECK: Ensure no duplicate user_id assignments exist before creating unique index
        duplicates = conn.execute(text("""
            SELECT user_id, COUNT(*)
            FROM employers
            WHERE user_id IS NOT NULL
            GROUP BY user_id
            HAVING COUNT(*) > 1
        """)).fetchall()

        if duplicates:
            dup_ids = [str(row[0]) for row in duplicates]
            raise RuntimeError(
                f"Migration 002 aborted: Detected duplicate employer profiles assigned to user_id(s): {', '.join(dup_ids)}."
            )

        # 5. SAFETY CHECK: Ensure all linked users actually have role 'employer'
        mismatches = conn.execute(text("""
            SELECT e.id, e.company_name, u.id, u.role
            FROM employers e
            JOIN users u ON e.user_id = u.id
            WHERE LOWER(u.role) != 'employer'
        """)).fetchall()

        if mismatches:
            mismatch_details = [f"employer id={row[0]} ('{row[1]}') -> user id={row[2]} (role='{row[3]}')" for row in mismatches]
            raise RuntimeError(
                f"Migration 002 aborted: Found employers linked to non-employer users: {', '.join(mismatch_details)}."
            )

        # 6. Add UNIQUE constraint and index on user_id
        indexes = [i['name'] for i in inspector.get_indexes('employers')]
        if 'ix_employers_user_id' not in indexes:
            op.create_index('ix_employers_user_id', 'employers', ['user_id'], unique=True)

        # 7. Add FOREIGN KEY constraint to users(id) ON DELETE CASCADE
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
