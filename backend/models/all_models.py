from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON, Boolean, Index
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from core.database import Base
import datetime
import enum

def _utcnow():
    """Timezone-aware UTC now, avoids DeprecationWarning on datetime.datetime.utcnow()."""
    return datetime.datetime.now(datetime.timezone.utc)

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    RECRUITER = "RECRUITER"

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # Relationships
    users = relationship("User", back_populates="organization")
    candidates = relationship("Candidate", back_populates="organization")
    job_requirements = relationship("JobRequirement", back_populates="organization")
    feedback = relationship("RecruiterFeedback", back_populates="organization")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default=UserRole.RECRUITER.value)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)

    organization = relationship("Organization", back_populates="users")

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    phone = Column(String, nullable=True)
    location = Column(String, nullable=True)
    
    # Deterministic fields calculated by code
    total_experience_years = Column(Float, nullable=True)
    relevant_experience_years = Column(Float, nullable=True)
    
    current_title = Column(String, nullable=True)
    current_company = Column(String, nullable=True)
    availability = Column(String, nullable=True)
    source = Column(String, nullable=True)
    
    # Enrichment Fields (Phase 6.5)
    social_links = Column(JSON, nullable=True) # e.g. {"github": "https://github.com/user"}
    external_evidence = Column(Text, nullable=True) # LLM audit of their open web footprint
    engineering_quality_score = Column(Float, nullable=True) # 0.0 to 1.0 based on code quality
    
    # Data Freshness Tracking (Phase 6.7)
    last_enriched_at = Column(DateTime, nullable=True) # When the profile was last refreshed
    staleness_score = Column(Float, nullable=True, default=1.0) # 0.0 = fresh, 1.0 = stale
    
    # Embeddings (summary vector)
    embedding = Column(Vector(1536), nullable=True) 
    
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # Relationships
    documents = relationship("CandidateDocument", back_populates="candidate", cascade="all, delete-orphan")
    skills = relationship("CandidateSkill", back_populates="candidate", cascade="all, delete-orphan")
    employments = relationship("Employment", back_populates="candidate", cascade="all, delete-orphan")
    demographics = relationship("CandidateDemographics", back_populates="candidate", uselist=False, cascade="all, delete-orphan")
    section_embeddings = relationship("CandidateSectionEmbedding", back_populates="candidate", cascade="all, delete-orphan")
    organization = relationship("Organization", back_populates="candidates")

    __table_args__ = (
        Index(
            "ix_candidates_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"}
        ),
    )

class CandidateDemographics(Base):
    __tablename__ = "candidate_demographics"
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), unique=True)
    
    gender = Column(String, nullable=True) # e.g. Male, Female, Non-Binary, Prefer Not To Say
    race_ethnicity = Column(String, nullable=True) # e.g. Asian, Black, Hispanic, White, Two or More, Prefer Not To Say
    veteran_status = Column(String, nullable=True)
    disability_status = Column(String, nullable=True)
    
    candidate = relationship("Candidate", back_populates="demographics")


class CandidateSectionEmbedding(Base):
    """
    Advanced Multi-Vector Chunked Embedding representation (ColBERT-style MaxSim).
    Stores distinct 1536-dim vector embeddings for separate candidate sections:
    SKILLS, SUMMARY, individual EMPLOYMENT roles, PROJECTS, and ENRICHMENT evidence.
    Solves the 'Lost in the Middle' problem.
    """
    __tablename__ = "candidate_section_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    
    section_type = Column(String, index=True) # 'SKILLS', 'SUMMARY', 'EXPERIENCE', 'PROJECT', 'ENRICHMENT'
    section_title = Column(String, nullable=True) # e.g. "Senior Backend Engineer at TechCorp"
    content_chunk = Column(Text) # Extracted section text
    embedding = Column(Vector(1536), nullable=True) # Dedicated embedding vector for THIS section
    
    created_at = Column(DateTime, default=_utcnow)

    candidate = relationship("Candidate", back_populates="section_embeddings")

    __table_args__ = (
        Index(
            "ix_candidate_section_embeddings_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"}
        ),
    )



class CandidateDocument(Base):
    __tablename__ = "candidate_documents"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), index=True, nullable=True)
    
    original_filename = Column(String)
    storage_key = Column(String, unique=True, index=True)
    mime_type = Column(String)
    file_size = Column(Integer)
    sha256_hash = Column(String, unique=True, index=True) # Used for deduplication
    
    # Text artifacts preserved for downstream LLM evaluation
    raw_extracted_text = Column(Text, nullable=True)
    normalized_text = Column(Text, nullable=True)
    
    # Processing state
    extraction_status = Column(String, default="PENDING")
    parsing_status = Column(String, default="PENDING")
    embedding_status = Column(String, default="PENDING")
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    candidate = relationship("Candidate", back_populates="documents")


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    canonical_skill_id = Column(Integer, ForeignKey("ontology.id"), nullable=True)
    
    original_extracted_skill = Column(String)
    category = Column(String, nullable=True)
    evidence_references = Column(JSON, nullable=True)
    years_of_experience = Column(Float, nullable=True)
    last_used = Column(DateTime, nullable=True)
    confidence = Column(Float, nullable=True)
    
    candidate = relationship("Candidate", back_populates="skills")
    canonical_skill = relationship("Ontology")


class Employment(Base):
    __tablename__ = "employment"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    
    company = Column(String)
    job_title = Column(String)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)
    extracted_skills = Column(JSON, nullable=True)
    evidence_references = Column(JSON, nullable=True)
    
    candidate = relationship("Candidate", back_populates="employments")


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id = Column(String, primary_key=True, index=True) # UUID
    document_id = Column(Integer, ForeignKey("candidate_documents.id"), nullable=True)
    
    stage = Column(String, default="UPLOADED") # UPLOADED, VALIDATING, EXTRACTING, NORMALIZING, PARSING, NORMALIZING_SKILLS, CALCULATING_EXPERIENCE, DEDUPLICATING, EMBEDDING, INDEXING
    status = Column(String, default="PENDING") # PENDING, IN_PROGRESS, COMPLETED, FAILED
    
    error_type = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    document = relationship("CandidateDocument")


# Existing Models
class JobRequirement(Base):
    __tablename__ = "job_requirements"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String)
    raw_description = Column(Text)
    mandatory_skills = Column(JSON) 
    preferred_skills = Column(JSON)
    min_experience_years = Column(Float)
    location_requirements = Column(String)
    embedding = Column(Vector(1536))
    created_at = Column(DateTime, default=_utcnow)
    organization = relationship("Organization", back_populates="job_requirements")

class Ontology(Base):
    __tablename__ = "ontology"

    id = Column(Integer, primary_key=True, index=True)
    canonical_name = Column(String, unique=True, index=True)
    category = Column(String) 
    aliases = Column(JSON) 
    embedding = Column(Vector(1536), nullable=True) 

class AIRegistry(Base):
    __tablename__ = "ai_registry"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String) 
    entity_id = Column(String) # Could be UUID or INT stringified
    provider = Column(String)
    model_name = Column(String)
    model_version = Column(String)
    embedding_model = Column(String, nullable=True)
    prompt_version = Column(String)
    pipeline_version = Column(String)
    input_hash = Column(String)
    output_data = Column(JSON)
    timestamp = Column(DateTime, default=_utcnow)
    latency = Column(Float, nullable=True)
    token_usage = Column(JSON, nullable=True)
    estimated_cost = Column(Float, nullable=True)

class EvaluationEvidence(Base):
    __tablename__ = "evaluation_evidence"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job_requirements.id"))
    candidate_id = Column(Integer, ForeignKey("candidates.id"))
    requirement = Column(String) 
    evidence_text = Column(Text) 
    assessment = Column(String) 
    confidence = Column(Float)
    validation_status = Column(String, default="UNVERIFIED") # PASS, FAIL, UNVERIFIED
    timestamp = Column(DateTime, default=_utcnow)
    
    job = relationship("JobRequirement")
    candidate = relationship("Candidate")

class RecruiterFeedback(Base):
    __tablename__ = "recruiter_feedback"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    job_id = Column(Integer, ForeignKey("job_requirements.id"))
    candidate_id = Column(Integer, ForeignKey("candidates.id"))
    feedback_type = Column(String) 
    comments = Column(Text)
    timestamp = Column(DateTime, default=_utcnow)
    organization = relationship("Organization", back_populates="feedback")

class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    id = Column(String, primary_key=True, index=True) # UUID
    job_type = Column(String, index=True) # e.g. "CV_INGESTION", "JD_PARSING"
    status = Column(String, default="QUEUED") # QUEUED, PROCESSING, COMPLETED, FAILED, CANCELLED
    
    payload = Column(JSON, nullable=True) # Input data
    result = Column(JSON, nullable=True) # Output data
    
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

