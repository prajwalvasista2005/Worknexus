"""normalize user roles and add check constraint

Revision ID: 004_normalize_roles
Revises: 003_case_insensitive_email
Create Date: 2026-09-28 23:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '004_normalize_roles'
down_revision: Union[str, Sequence[str], None] = '003_case_insensitive_email'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'users' in tables:
        # 1. Normalize all existing roles to lowercase trimmed
        conn.execute(text("""
            UPDATE users
            SET role = LOWER(TRIM(role))
            WHERE role != LOWER(TRIM(role));
        """))

        # 2. Add CHECK constraint enforcing allowed canonical roles
        if conn.dialect.name == "postgresql":
            # Check if constraint exists first
            check_query = text("""
                SELECT 1 FROM pg_constraint
                WHERE conname = 'chk_users_role'
            """)
            exists = conn.execute(check_query).scalar()
            if not exists:
                conn.execute(text("""
                    ALTER TABLE users
                    ADD CONSTRAINT chk_users_role
                    CHECK (role IN ('student', 'employer', 'institute', 'trainer', 'admin'));
                """))
        else:
            try:
                op.create_check_constraint(
                    "chk_users_role",
                    "users",
                    "role IN ('student', 'employer', 'institute', 'trainer', 'admin')"
                )
            except Exception:
                pass


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'users' in tables:
        if conn.dialect.name == "postgresql":
            conn.execute(text("ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_role;"))
        else:
            try:
                op.drop_constraint("chk_users_role", "users", type_="check")
            except Exception:
                pass
