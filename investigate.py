from core.database import SessionLocal
from models.all_models import Candidate, CandidateDocument
from sqlalchemy import func
db = SessionLocal()

print('--- INVESTIGATING MISSING EMBEDDINGS (15 Candidates) ---')
no_emb = db.query(Candidate).filter(Candidate.embedding == None).limit(10).all()
for c in no_emb:
    doc = db.query(CandidateDocument).filter(CandidateDocument.candidate_id == c.id).first()
    text_len = len(doc.raw_extracted_text) if doc and doc.raw_extracted_text else 0
    print(f'Candidate ID: {c.id}, Name: {c.name}, Source: {c.source}, Document Text Length: {text_len}')

print('\n--- INVESTIGATING EXTRA DOCUMENTS ---')
total_docs = db.query(CandidateDocument).count()
total_cands = db.query(Candidate).count()

# 1. Orphan documents
orphan_count = db.query(CandidateDocument).filter(~CandidateDocument.candidate_id.in_(db.query(Candidate.id))).count()
print(f'Orphan Documents (Candidate deleted but doc remains): {orphan_count}')

# 2. Candidates with multiple documents
multi_docs = db.query(
    CandidateDocument.candidate_id, func.count(CandidateDocument.id).label('doc_count')
).group_by(CandidateDocument.candidate_id).having(func.count(CandidateDocument.id) > 1).all()

print(f'Number of Candidates with MULTIPLE documents: {len(multi_docs)}')
if multi_docs:
    print('Examples of candidates with multiple docs:')
    for cid, count in multi_docs[:5]:
        c = db.get(Candidate, cid)
        name = c.name if c else 'Unknown/Deleted'
        print(f'  - Candidate ID: {cid}, Name: {name}, Doc Count: {count}')

db.close()
