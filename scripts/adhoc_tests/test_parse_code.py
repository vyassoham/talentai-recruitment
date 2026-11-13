import os
import sys
# Set up paths so we can import from backend
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from sqlalchemy.orm import Session
from backend.core.database import SessionLocal
from backend.services.jobs.job_service import JobService

def test():
    db = SessionLocal()
    try:
        svc = JobService(db)
        actual_description = 'Looking for a Python dev with FastAPI'
        job = svc.process_raw_jd(actual_description)
        print("JOB ID:", job.id)
        
        reqs = []
        for m in (job.mandatory_skills or []):
            reqs.append({'name': m.get('canonical_skill_name'), 'type': 'MANDATORY', 'weight': 1.0})
        for p in (job.preferred_skills or []):
            reqs.append({'name': p.get('canonical_skill_name'), 'type': 'PREFERRED', 'weight': 0.5})
            
        print("REQS:", reqs)
    except Exception as e:
        print("ERROR:", e)
        import traceback
        traceback.print_exc()
    finally:
        db.close()

test()
