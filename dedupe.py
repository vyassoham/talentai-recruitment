from core.database import SessionLocal
from models.all_models import Candidate, CandidateDocument, CandidateSkill, Employment, CandidateDemographics, RecruiterFeedback
from sqlalchemy import text
from collections import defaultdict
import time

def dedupe():
    db = SessionLocal()
    print("Fetching candidates and documents...")
    cands = db.query(Candidate).all()
    docs = db.query(CandidateDocument).all()
    
    # Map candidate_id -> list of file sizes
    cand_doc_sizes = defaultdict(list)
    for d in docs:
        if d.candidate_id and d.file_size:
            cand_doc_sizes[d.candidate_id].append(d.file_size)
            
    # Group by (lower_name, first_file_size)
    groups = defaultdict(list)
    for c in cands:
        name = c.name.strip().lower() if c.name else "unknown"
        sizes = cand_doc_sizes.get(c.id, [0])
        # Use the first size, or 0 if none
        size = sizes[0] if sizes else 0
        
        # We group by name and size. If size is 0 (no doc), we group by name only if we want,
        # but let's stick to (name, size).
        key = (name, size)
        groups[key].append(c.id)
        
    duplicates_to_delete = []
    for key, ids in groups.items():
        if len(ids) > 1:
            # Sort IDs to keep the oldest one (lowest ID)
            ids.sort()
            # Keep the first, mark rest for deletion
            duplicates_to_delete.extend(ids[1:])
            
    print(f"Found {len(duplicates_to_delete)} duplicate candidates to remove.")
    
    deleted_count = 0
    for cid in duplicates_to_delete:
        try:
            # Delete related
            db.query(CandidateSkill).filter(CandidateSkill.candidate_id == cid).delete(synchronize_session=False)
            db.query(Employment).filter(Employment.candidate_id == cid).delete(synchronize_session=False)
            db.query(CandidateDemographics).filter(CandidateDemographics.candidate_id == cid).delete(synchronize_session=False)
            db.query(RecruiterFeedback).filter(RecruiterFeedback.candidate_id == cid).delete(synchronize_session=False)
            db.execute(text(f"DELETE FROM evaluation_evidence WHERE candidate_id = {cid}"))
            db.query(CandidateDocument).filter(CandidateDocument.candidate_id == cid).delete(synchronize_session=False)
            
            # Delete candidate
            c = db.get(Candidate, cid)
            if c:
                db.delete(c)
                
            deleted_count += 1
            if deleted_count % 100 == 0:
                db.commit()
                print(f"Deleted {deleted_count} duplicates...")
        except Exception as e:
            db.rollback()
            print(f"Error deleting candidate {cid}: {e}")
            
    db.commit()
    db.close()
    print(f"Successfully deleted {deleted_count} duplicates!")

if __name__ == '__main__':
    start = time.time()
    dedupe()
    print(f"Took {time.time() - start:.2f} seconds.")
