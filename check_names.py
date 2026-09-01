from core.database import SessionLocal
from models.all_models import Candidate
import re

db = SessionLocal()
cands = db.query(Candidate.id, Candidate.name).all()

bad_keywords = ['experience', 'developer', 'engineer', 'knowledge', 'technolog', 'resume', 'curriculum', 'profile', 'summary', 'architect', 'years', 'yrs', 'senior', 'junior', 'lead', 'software', 'project', 'detail', 'personal']

bad_cands = []
for cid, name in cands:
    if not name:
        bad_cands.append((cid, name))
        continue
        
    lower_name = name.lower()
    
    # 1. Contains bad keywords
    if any(k in lower_name for k in bad_keywords):
        bad_cands.append((cid, name))
        continue
        
    # 2. Contains numbers
    if re.search(r'\d', name):
        bad_cands.append((cid, name))
        continue
        
    # 3. Too long
    if len(name.split()) > 4:
        bad_cands.append((cid, name))
        continue

print(f'Total candidates: {len(cands)}')
print(f'Bad names detected: {len(bad_cands)}')
print('Samples of bad names:')
for c in bad_cands[:20]:
    print(f'  - {c[1]}')
