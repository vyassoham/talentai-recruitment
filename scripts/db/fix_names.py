import os
from dotenv import load_dotenv
load_dotenv('backend/.env')
print("API KEY:", os.getenv('GEMINI_API_KEY')[:5] if os.getenv('GEMINI_API_KEY') else "None")

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.database import SessionLocal
from models.all_models import Candidate, CandidateDocument
from services.ai.provider import get_ai_provider
from pydantic import BaseModel

class ExtractedName(BaseModel):
    correct_name: str

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

db = SessionLocal()
all_cands = db.query(Candidate).all()
bad_cands = [c for c in all_cands if is_bad_name(c.name)]
print(f"Total bad names to fix: {len(bad_cands)}")

provider = get_ai_provider()
print(f"Using provider: {provider.model_name}")

def fix_name(cid):
    local_db = SessionLocal()
    try:
        cand = local_db.get(Candidate, cid)
        doc = local_db.query(CandidateDocument).filter(CandidateDocument.candidate_id == cid).first()
        if not doc or not doc.raw_extracted_text:
            local_db.close()
            return False
            
        text_chunk = doc.raw_extracted_text[:1500]
        prompt = f"Extract the REAL name of the candidate from the beginning of this CV. Return ONLY the name. Do NOT return their title, 'resume', or words like 'Senior'. If no valid name is found, guess based on common names or return 'Unknown'.\n\nCV Text:\n{text_chunk}"
        
        result, _ = provider.generate_structured(prompt, ExtractedName, "You are a precise data extractor.")
        new_name = result.correct_name.strip()
        
        if new_name and len(new_name) > 2 and 'developer' not in new_name.lower() and 'experience' not in new_name.lower():
            cand.name = new_name
            local_db.commit()
            local_db.close()
            return True
            
        local_db.close()
        return False
    except Exception as e:
        local_db.close()
        return False

# Execute in parallel
success = 0
start = time.time()
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(fix_name, c.id) for c in bad_cands]
    for i, f in enumerate(as_completed(futures)):
        if f.result():
            success += 1
        if i % 10 == 0:
            print(f"Processed {i}/{len(bad_cands)}")
            
print(f"Successfully fixed {success} names in {time.time() - start:.2f} seconds.")
db.close()
