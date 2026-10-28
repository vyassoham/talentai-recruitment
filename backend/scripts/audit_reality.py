import os
import sys
import re
from dotenv import load_dotenv

load_dotenv('D:/recruitment_platform/backend/.env')
sys.path.insert(0, 'D:/recruitment_platform/backend')

from core.database import SessionLocal
from models.all_models import Candidate, CandidateDocument, CandidateSkill, CandidateDemographics, CandidateSectionEmbedding, User

def run_audit():
    db = SessionLocal()
    
    total_cands = db.query(Candidate).count()
    total_docs = db.query(CandidateDocument).count()
    total_skills = db.query(CandidateSkill).count()
    total_users = db.query(User).count()
    
    with_email = db.query(Candidate).filter(Candidate.email.isnot(None), Candidate.email != '').count()
    with_phone = db.query(Candidate).filter(Candidate.phone.isnot(None), Candidate.phone != '').count()
    with_both = db.query(Candidate).filter(
        Candidate.email.isnot(None), Candidate.email != '',
        Candidate.phone.isnot(None), Candidate.phone != ''
    ).count()
    
    with_emb = db.query(Candidate).filter(Candidate.embedding.isnot(None)).count()
    section_embs = db.query(CandidateSectionEmbedding).count()
    
    # Check bad names
    bad_pattern = (
        Candidate.name.ilike('%India%') | 
        Candidate.name.ilike('%Bangalore%') | 
        Candidate.name.ilike('%Resume%') | 
        Candidate.name.ilike('%Profile%') | 
        Candidate.name.ilike('%Maintaining%') |
        Candidate.name.ilike('%Documentation%') |
        Candidate.name.ilike('%Keyimpact%') |
        Candidate.name.ilike('%Curriculum%') |
        Candidate.name.ilike('%Karnataka%')
    )
    bad_cands = db.query(Candidate).filter(bad_pattern).all()
    
    synthetic_seeds = db.query(Candidate).filter(Candidate.name.ilike('%Fit%')).all()
    
    # Check how many bad candidates have real emails
    bad_with_email = [c for c in bad_cands if c.email]
    
    print("=" * 60)
    print("TALENTAI FORENSIC REALITY AUDIT")
    print("=" * 60)
    print(f"Total Candidates in Database:      {total_cands}")
    print(f"Total Candidate Documents (PDFs):  {total_docs}")
    print(f"Total Extracted Technical Skills:  {total_skills}")
    print(f"Candidates with Real Email:        {with_email} ({round(with_email/total_cands*100, 1)}%)")
    print(f"Candidates with Real Phone:        {with_phone} ({round(with_phone/total_cands*100, 1)}%)")
    print(f"Candidates with Both Email+Phone:  {with_both} ({round(with_both/total_cands*100, 1)}%)")
    print(f"Synthetic Mock Test Candidates:    {len(synthetic_seeds)}")
    print(f"Candidates with Corrupt Names:     {len(bad_cands)} ({round(len(bad_cands)/total_cands*100, 1)}%)")
    print(f"Corrupt Name Cands with Real Email: {len(bad_with_email)} ({round(len(bad_with_email)/len(bad_cands)*100, 1)}%)")
    print(f"Candidates with Vector Embeddings: {with_emb} ({round(with_emb/total_cands*100, 2)}%)")
    print(f"Total Section Embeddings:          {section_embs}")
    print(f"Total Registered Users:            {total_users}")
    print("=" * 60)
    
    print("\nSAMPLE REPAIRS (Corrupt Name -> Genuine Person from Email):")
    for c in bad_with_email[:10]:
        username = c.email.split('@')[0]
        clean_user = re.sub(r'[0-9_\-]+', ' ', username).strip()
        parts = [p.capitalize() for p in clean_user.split() if len(p) >= 2]
        inferred = ' '.join(parts) if parts else "Unknown"
        print(f"  ID {c.id}: Current Name: \"{c.name}\" --> Real Name: \"{inferred}\" (Email: {c.email})")

    db.close()

if __name__ == '__main__':
    run_audit()
