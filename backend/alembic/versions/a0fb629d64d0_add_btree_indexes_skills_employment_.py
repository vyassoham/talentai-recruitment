"""add_btree_indexes_skills_employment_experience

Revision ID: a0fb629d64d0
Revises: 3c0870e56dbb
Create Date: 2026-08-19 09:58:34.301527

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a0fb629d64d0'
down_revision: Union[str, Sequence[str], None] = '3c0870e56dbb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with performance B-Tree indexes for fast range and join filtering."""
    # B-Tree index on candidate_skills canonical_skill_id
    op.create_index(
        'ix_candidate_skills_canonical_skill_id',
        'candidate_skills',
        ['canonical_skill_id'],
        unique=False
    )
    
    # B-Tree index on candidate_skills years_of_experience
    op.create_index(
        'ix_candidate_skills_years_of_experience',
        'candidate_skills',
        ['years_of_experience'],
        unique=False
    )
    
    # Compound B-Tree index on candidate_skills (candidate_id, canonical_skill_id)
    op.create_index(
        'ix_candidate_skills_cand_canonical',
        'candidate_skills',
        ['candidate_id', 'canonical_skill_id'],
        unique=False
    )
    
    # B-Tree index on employment candidate_id (if not already indexed)
    op.create_index(
        'ix_employment_candidate_id',
        'employment',
        ['candidate_id'],
        unique=False,
        if_not_exists=True
    )
    
    # B-Tree index on candidates total_experience_years for SQL pre-filtering
    op.create_index(
        'ix_candidates_total_experience_years',
        'candidates',
        ['total_experience_years'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_candidates_total_experience_years', table_name='candidates')
    op.drop_index('ix_employment_candidate_id', table_name='employment')
    op.drop_index('ix_candidate_skills_cand_canonical', table_name='candidate_skills')
    op.drop_index('ix_candidate_skills_years_of_experience', table_name='candidate_skills')
    op.drop_index('ix_candidate_skills_canonical_skill_id', table_name='candidate_skills')
