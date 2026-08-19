"""add_compound_indexes_evidence_feedback

Revision ID: 7453938e33a3
Revises: a0fb629d64d0
Create Date: 2026-08-19 10:09:45.386535

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7453938e33a3'
down_revision: Union[str, Sequence[str], None] = 'a0fb629d64d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with compound B-Tree indexes for evaluation evidence and feedback."""
    op.create_index(
        'ix_evaluation_evidence_job_cand',
        'evaluation_evidence',
        ['job_id', 'candidate_id'],
        unique=False
    )
    
    op.create_index(
        'ix_recruiter_feedback_job_cand',
        'recruiter_feedback',
        ['job_id', 'candidate_id'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_recruiter_feedback_job_cand', table_name='recruiter_feedback')
    op.drop_index('ix_evaluation_evidence_job_cand', table_name='evaluation_evidence')
