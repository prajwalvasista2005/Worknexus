"""001_phase10_student_role_schema

Revision ID: 001_phase10
Revises: None
Create Date: 2026-09-20 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001_phase10'
down_revision = '49ecdd8f4657'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. target_roles table
    op.create_table(
        'target_roles',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )

    # 2. role_skills table (Many-to-Many between TargetRole and Skill)
    op.create_table(
        'role_skills',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('role_id', sa.String(length=64), sa.ForeignKey('target_roles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('skill_id', sa.String(length=64), sa.ForeignKey('skills.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('role_id', 'skill_id', name='uq_role_skill')
    )
    op.create_index('ix_role_skills_role_id', 'role_skills', ['role_id'])
    op.create_index('ix_role_skills_skill_id', 'role_skills', ['skill_id'])

    # 3. student_profiles table (Extends User with role='Student')
    op.create_table(
        'student_profiles',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('target_role_id', sa.String(length=64), sa.ForeignKey('target_roles.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_student_profiles_user_id', 'student_profiles', ['user_id'])
    op.create_index('ix_student_profiles_target_role_id', 'student_profiles', ['target_role_id'])

    # 4. student_skill_evidence table (Categorical Skill Evidence)
    op.create_table(
        'student_skill_evidence',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('student_profile_id', sa.Integer(), sa.ForeignKey('student_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('skill_id', sa.String(length=64), sa.ForeignKey('skills.id', ondelete='CASCADE'), nullable=False),
        sa.Column('evidence_type', sa.String(length=32), nullable=False),
        sa.Column('strength', sa.String(length=16), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_student_skill_evidence_profile_id', 'student_skill_evidence', ['student_profile_id'])
    op.create_index('ix_student_skill_evidence_skill_id', 'student_skill_evidence', ['skill_id'])

def downgrade() -> None:
    op.drop_table('student_skill_evidence')
    op.drop_table('student_profiles')
    op.drop_table('role_skills')
    op.drop_table('target_roles')
