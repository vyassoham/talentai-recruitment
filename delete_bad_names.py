from core.database import SessionLocal
from models.all_models import Candidate, CandidateDocument, CandidateSkill, Employment, CandidateDemographics, RecruiterFeedback
from sqlalchemy import text
import re

db = SessionLocal()
cands = db.query(Candidate.id, Candidate.name).all()

bad_keywords = ['experience', 'developer', 'engineer', 'knowledge', 'technolog', 'resume', 'curriculum', 'profile', 'summary', 'architect', 'years', 'yrs', 'senior', 'junior', 'lead', 'software', 'project', 'detail', 'personal', 'bachelor', 'work', 'education']

def is_bad_name(name):
    if not name: return True
    lower_name = name.lower()
    if any(k in lower_name for k in bad_keywords): return True
    if re.search(r'\d', name): return True
    if len(name.split()) > 4: return True
    if re.search(r'^([A-F0-9]{2,}\s*)+$', name): return True
    if len(name) < 3: return True
    return False

bad_cids = [c[0] for c in cands if is_bad_name(c[1])]
print(f'Deleting {len(bad_cids)} candidates with unrecoverable garbage names...')

deleted = 0
for cid in bad_cids:
    try:
        db.query(CandidateSkill).filter(CandidateSkill.candidate_id == cid).delete(synchronize_session=False)
        db.query(Employment).filter(Employment.candidate_id == cid).delete(synchronize_session=False)
        db.query(CandidateDemographics).filter(CandidateDemographics.candidate_id == cid).delete(synchronize_session=False)
        db.query(RecruiterFeedback).filter(RecruiterFeedback.candidate_id == cid).delete(synchronize_session=False)
        db.execute(text(f'DELETE FROM evaluation_evidence WHERE candidate_id = {cid}'))
        db.query(CandidateDocument).filter(CandidateDocument.candidate_id == cid).delete(synchronize_session=False)
        db.query(Candidate).filter(Candidate.id == cid).delete(synchronize_session=False)
        deleted += 1
    except Exception as e:
        db.rollback()
        print(f'Error on {cid}: {e}')

db.commit()
print(f'Successfully deleted {deleted} garbage candidates.')
db.close()
