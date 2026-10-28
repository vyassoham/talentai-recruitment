"""add_multitenant_organizations

Revision ID: e101_multitenant_orgs
Revises: 7453938e33a3
Create Date: 2026-10-28 21:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e101_multitenant_orgs'
down_revision: Union[str, Sequence[str], None] = '7453938e33a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create organizations table
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(length=64), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=128), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    op.create_index('ix_organizations_id', 'organizations', ['id'], unique=False)
    op.create_index('ix_organizations_slug', 'organizations', ['slug'], unique=True)

    # 2. Insert Default Enterprise Organization
    op.execute(
        "INSERT INTO organizations (id, name, slug, is_active) "
        "VALUES ('org_talentai_default', 'TalentAI Enterprise (Default)', 'talentai-default', true) "
        "ON CONFLICT (id) DO NOTHING;"
    )

    # 3. Add organization_id column to users
    op.add_column('users', sa.Column('organization_id', sa.String(length=64), sa.ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True))
    op.create_index('ix_users_organization_id', 'users', ['organization_id'], unique=False)

    # 4. Add organization_id column to candidates
    op.add_column('candidates', sa.Column('organization_id', sa.String(length=64), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True))
    op.create_index('ix_candidates_organization_id', 'candidates', ['organization_id'], unique=False)

    # 5. Add organization_id column to job_requirements
    op.add_column('job_requirements', sa.Column('organization_id', sa.String(length=64), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True))
    op.create_index('ix_job_requirements_organization_id', 'job_requirements', ['organization_id'], unique=False)

    # 6. Add organization_id column to recruiter_feedback
    op.add_column('recruiter_feedback', sa.Column('organization_id', sa.String(length=64), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True))
    op.create_index('ix_recruiter_feedback_organization_id', 'recruiter_feedback', ['organization_id'], unique=False)

    # 7. Backfill all existing records to the default organization
    op.execute("UPDATE users SET organization_id = 'org_talentai_default' WHERE organization_id IS NULL;")
    op.execute("UPDATE candidates SET organization_id = 'org_talentai_default' WHERE organization_id IS NULL;")
    op.execute("UPDATE job_requirements SET organization_id = 'org_talentai_default' WHERE organization_id IS NULL;")
    op.execute("UPDATE recruiter_feedback SET organization_id = 'org_talentai_default' WHERE organization_id IS NULL;")


def downgrade() -> None:
    op.drop_index('ix_recruiter_feedback_organization_id', table_name='recruiter_feedback')
    op.drop_column('recruiter_feedback', 'organization_id')

    op.drop_index('ix_job_requirements_organization_id', table_name='job_requirements')
    op.drop_column('job_requirements', 'organization_id')

    op.drop_index('ix_candidates_organization_id', table_name='candidates')
    op.drop_column('candidates', 'organization_id')

    op.drop_index('ix_users_organization_id', table_name='users')
    op.drop_column('users', 'organization_id')

    op.drop_index('ix_organizations_slug', table_name='organizations')
    op.drop_index('ix_organizations_id', table_name='organizations')
    op.drop_table('organizations')
