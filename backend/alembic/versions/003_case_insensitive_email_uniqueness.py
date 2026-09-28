"""add case-insensitive unique email index and normalize user emails

Revision ID: 003_case_insensitive_email
Revises: 002_employer_user_id
Create Date: 2026-09-28 23:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '003_case_insensitive_email'
down_revision: Union[str, Sequence[str], None] = '002_employer_user_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'users' in tables:
        # 1. Deduplicate legacy users with the same lowercased email, keeping the lowest id
        conn.execute(text("""
            DELETE FROM users
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM users
                GROUP BY LOWER(TRIM(email))
            );
        """))

        # 2. Normalize all remaining emails to lowercase and trimmed
        conn.execute(text("""
            UPDATE users
            SET email = LOWER(TRIM(email))
            WHERE email != LOWER(TRIM(email));
        """))

        # 3. Create functional unique index on LOWER(email)
        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email_lower ON users (LOWER(email));
        """))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'users' in tables:
        conn.execute(text("DROP INDEX IF EXISTS ix_users_email_lower;"))
