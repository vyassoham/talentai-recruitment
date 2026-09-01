from core.database import SessionLocal
from models.all_models import Candidate, CandidateDocument
import re

db = SessionLocal()
# Fetch all candidates that lack email or phone but have documents
cands = db.query(Candidate).filter((Candidate.email == None) | (Candidate.phone == None)).all()
print(f"Found {len(cands)} candidates missing contact info.")

updated = 0
for c in cands:
    doc = db.query(CandidateDocument).filter(CandidateDocument.candidate_id == c.id).first()
    if not doc or not doc.raw_extracted_text: continue
    
    text = doc.raw_extracted_text
    
    if not c.email:
        emails = re.findall(r'[\w\.-]+@[\w\.-]+', text)
        if emails:
            c.email = emails[0]
            
    if not c.phone:
        # Matches formats like +91 9876543210, 98765-43210, etc.
        phones = re.findall(r'(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{3,4}[\s-]?\d{3,4}', text)
        # Filter realistic phone lengths (10-14 digits)
        valid_phones = []
        for p in phones:
            digits = re.sub(r'\D', '', p)
            if 10 <= len(digits) <= 14:
                valid_phones.append(p.strip())
        
        if valid_phones:
            c.phone = valid_phones[0]
            
    if c.email or c.phone:
        updated += 1
        
    if updated % 500 == 0:
        db.commit()

db.commit()
print(f"Successfully backfilled contact info for {updated} candidates.")
