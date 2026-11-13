from core.database import SessionLocal
from models.all_models import Candidate, CandidateDocument
import re

db = SessionLocal()
docs = db.query(CandidateDocument).limit(500).all()
found_emails = []
for doc in docs:
    if not doc.raw_extracted_text: continue
    emails = re.findall(r'[\w\.-]+@[\w\.-]+', doc.raw_extracted_text)
    if emails:
        c = db.get(Candidate, doc.candidate_id)
        if c:
            found_emails.append((c.name, emails[0], c.email, c.phone))

for item in found_emails[:10]:
    print(f"Name: {item[0]}, Extracted: {item[1]}, DB Email: {item[2]}, DB Phone: {item[3]}")
