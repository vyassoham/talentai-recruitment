from core.database import SessionLocal
from models.all_models import Candidate
db = SessionLocal()
cands = db.query(Candidate).filter(Candidate.embedding != None).count()
total = db.query(Candidate).count()
print(f"Candidates with embeddings: {cands} / {total}")
