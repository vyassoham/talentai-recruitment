from core.database import SessionLocal
from models.all_models import Candidate, CandidateSkill, Employment, CandidateDemographics, RecruiterFeedback
from sqlalchemy import text
db = SessionLocal()
candidates = db.query(Candidate).all()
for d in candidates:
    if 'Perfect Fit' in d.name or 'Good Fit' in d.name or 'Okay Fit' in d.name or 'Poor Fit' in d.name or 'Irrelevant' in d.name or d.name in ['Alice', 'Bob', 'Eve', 'Mallory', 'Trent']:
        print(f'Deleting {d.name}...')
        db.execute(text(f'DELETE FROM evaluation_evidence WHERE candidate_id = {d.id}'))
        db.query(RecruiterFeedback).filter(RecruiterFeedback.candidate_id == d.id).delete()
        db.query(CandidateSkill).filter(CandidateSkill.candidate_id == d.id).delete()
        db.query(Employment).filter(Employment.candidate_id == d.id).delete()
        db.query(CandidateDemographics).filter(CandidateDemographics.candidate_id == d.id).delete()
        db.execute(text(f'DELETE FROM candidate_documents WHERE candidate_id = {d.id}'))
        db.delete(d)
db.commit()
print('Done!')
