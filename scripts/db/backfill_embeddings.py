from core.database import SessionLocal
from models.all_models import Candidate
from services.ai.provider import get_ai_provider
from services.ai.embeddings import EmbeddingsService
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

db = SessionLocal()
cands = db.query(Candidate).filter(Candidate.embedding == None).all()
db.close()
print(f"Found {len(cands)} candidates missing embeddings.")

def process_chunk(c_ids):
    local_db = SessionLocal()
    success = 0
    for cid in c_ids:
        try:
            EmbeddingsService.generate_candidate_embedding(local_db, cid)
            success += 1
        except Exception as e:
            pass
    local_db.close()
    return success

chunk_size = 50
chunks = [ [c.id for c in cands[i:i+chunk_size]] for i in range(0, len(cands), chunk_size) ]

total = 0
start = time.time()
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = {executor.submit(process_chunk, ch): ch for ch in chunks}
    for f in as_completed(futures):
        total += f.result()
        print(f"Progress: {total}/{len(cands)}")
        
print(f"Finished backfilling {total} embeddings in {time.time() - start:.2f} seconds.")
