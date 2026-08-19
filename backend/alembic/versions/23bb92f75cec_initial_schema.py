"""Initial Schema

Revision ID: 23bb92f75cec
Revises: 
Create Date: 2026-08-18 18:39:41.341381

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision = '23bb92f75cec'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure pgvector extension exists
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    op.create_table('ontology',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('canonical_name', sa.String(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('aliases', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ontology_canonical_name'), 'ontology', ['canonical_name'], unique=True)
    op.create_index(op.f('ix_ontology_id'), 'ontology', ['id'], unique=False)

    op.create_table('candidates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('total_experience_years', sa.Float(), nullable=True),
        sa.Column('relevant_experience_years', sa.Float(), nullable=True),
        sa.Column('current_title', sa.String(), nullable=True),
        sa.Column('current_company', sa.String(), nullable=True),
        sa.Column('availability', sa.String(), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidates_email'), 'candidates', ['email'], unique=True)
    op.create_index(op.f('ix_candidates_id'), 'candidates', ['id'], unique=False)
    op.create_index(op.f('ix_candidates_name'), 'candidates', ['name'], unique=False)

    op.create_table('candidate_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=True),
        sa.Column('original_filename', sa.String(), nullable=True),
        sa.Column('storage_key', sa.String(), nullable=True),
        sa.Column('mime_type', sa.String(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('sha256_hash', sa.String(), nullable=True),
        sa.Column('raw_extracted_text', sa.Text(), nullable=True),
        sa.Column('normalized_text', sa.Text(), nullable=True),
        sa.Column('extraction_status', sa.String(), nullable=True),
        sa.Column('parsing_status', sa.String(), nullable=True),
        sa.Column('embedding_status', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidate_documents_id'), 'candidate_documents', ['id'], unique=False)
    op.create_index(op.f('ix_candidate_documents_storage_key'), 'candidate_documents', ['storage_key'], unique=True)
    op.create_index(op.f('ix_candidate_documents_sha256_hash'), 'candidate_documents', ['sha256_hash'], unique=True)

    op.create_table('candidate_skills',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=True),
        sa.Column('canonical_skill_id', sa.Integer(), nullable=True),
        sa.Column('original_extracted_skill', sa.String(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('evidence_references', sa.JSON(), nullable=True),
        sa.Column('years_of_experience', sa.Float(), nullable=True),
        sa.Column('last_used', sa.DateTime(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['canonical_skill_id'], ['ontology.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidate_skills_id'), 'candidate_skills', ['id'], unique=False)

    op.create_table('employment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=True),
        sa.Column('company', sa.String(), nullable=True),
        sa.Column('job_title', sa.String(), nullable=True),
        sa.Column('start_date', sa.DateTime(), nullable=True),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('extracted_skills', sa.JSON(), nullable=True),
        sa.Column('evidence_references', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_employment_id'), 'employment', ['id'], unique=False)

    op.create_table('ingestion_jobs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('stage', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('error_type', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['candidate_documents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ingestion_jobs_id'), 'ingestion_jobs', ['id'], unique=False)


def downgrade() -> None:
    op.drop_table('ingestion_jobs')
    op.drop_table('employment')
    op.drop_table('candidate_skills')
    op.drop_table('candidate_documents')
    op.drop_table('candidates')
    op.drop_table('ontology')
