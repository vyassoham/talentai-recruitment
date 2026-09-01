from core.database import SessionLocal
from models.all_models import Candidate, CandidateDocument
db = SessionLocal()
c = db.query(Candidate).filter(Candidate.name.ilike('%Jagdish%')).first()
if c:
    doc = db.query(CandidateDocument).filter(CandidateDocument.candidate_id == c.id).first()
    if doc:
        print(doc.raw_extracted_text[:1000])
