from core.database import SessionLocal
from models.all_models import Candidate, CandidateDocument
db = SessionLocal()
total = db.query(Candidate).count()
with_embeddings = db.query(Candidate).filter(Candidate.embedding != None).count()
with_docs = db.query(CandidateDocument).count()
print(f"Total Candidates: {total}")
print(f"Candidates with Embeddings: {with_embeddings}")
print(f"Total CV Documents: {with_docs}")
db.close()
