from core.database import SessionLocal
from models.all_models import Candidate
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

bad_cands = [c for c in cands if is_bad_name(c[1])]
print(f'Remaining bad names: {len(bad_cands)}')

db.close()
