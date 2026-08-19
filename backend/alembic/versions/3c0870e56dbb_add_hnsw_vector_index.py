"""add_hnsw_vector_index

Revision ID: 3c0870e56dbb
Revises: da7c8fe0dd16
Create Date: 2026-08-19 09:55:26.256140

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c0870e56dbb'
down_revision: Union[str, Sequence[str], None] = 'da7c8fe0dd16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with pgvector HNSW index for fast approximate nearest neighbor search."""
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_candidates_embedding_hnsw "
        "ON candidates USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64);"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ix_candidates_embedding_hnsw;")
