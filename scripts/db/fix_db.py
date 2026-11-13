from core.database import SessionLocal
from models.all_models import CandidateDocument, Candidate, IngestionJob
from services.ai.embeddings import EmbeddingsService

db = SessionLocal()

# Delete ingestion jobs linked to orphaned docs
db.query(IngestionJob).filter(
    IngestionJob.document_id.in_(
        db.query(CandidateDocument.id).filter(CandidateDocument.candidate_id == None)
    )
).delete(synchronize_session=False)

# Delete orphan docs
orphans = db.query(CandidateDocument).filter(CandidateDocument.candidate_id == None).delete(synchronize_session=False)
db.commit()
print(f"Deleted {orphans} orphaned documents with NULL candidate_id.")

# Retry embeddings for 15 candidates
missing = db.query(Candidate).filter(Candidate.embedding == None).all()
success = 0
for c in missing:
    try:
        EmbeddingsService.generate_candidate_embedding(db, c.id)
        success += 1
    except Exception as e:
        print(f"Failed to embed candidate {c.id}: {e}")
print(f"Successfully backfilled embeddings for {success} out of {len(missing)} candidates.")

db.close()
