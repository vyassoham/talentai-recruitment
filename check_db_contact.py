from core.database import SessionLocal
from models.all_models import Candidate, CandidateDocument
db = SessionLocal()
c = db.query(Candidate).filter(Candidate.name.ilike('%Jagdish%')).first()
if c:
    doc = db.query(CandidateDocument).filter(CandidateDocument.candidate_id == c.id).first()
    if doc:
        import re
        emails = re.findall(r'[\w\.-]+@[\w\.-]+', doc.raw_extracted_text)
        phones = re.findall(r'\+?\d[\d -]{8,12}\d', doc.raw_extracted_text)
        print("Emails:", emails)
        print("Phones:", phones)
