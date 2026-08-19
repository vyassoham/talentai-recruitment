import os
import sys
from sqlalchemy.orm import Session
from unittest.mock import MagicMock

# Ensure backend directory is in the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.jobs.job_service import JobService
from services.ai.jd_parser import JDParser
from models.all_models import JobRequirement

JDS = [
    """
    Title: Senior Python Backend Developer
    We are looking for a Senior Backend Developer with at least 6 years of professional experience.
    You MUST have deep expertise in Python and Django. 
    Experience with AWS and Kubernetes is highly preferred.
    Domain knowledge in Fintech is a huge plus.
    """,
    """
    Title: Full Stack Engineer
    Required: 3+ years experience with React and Node.js. 
    Strong communication skills are essential.
    Familiarity with PostgreSQL is preferred.
    """
]

def run_live_test():
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable is not set. Cannot run live test.")
        return

    # Mock DB session since we just want to verify the LLM extraction logic
    mock_db = MagicMock(spec=Session)
    
    # We will capture what the job service tries to add to the DB
    saved_jobs = []
    def mock_add(obj):
        if isinstance(obj, JobRequirement):
            saved_jobs.append(obj)
            
    mock_db.add.side_effect = mock_add
    
    service = JobService(mock_db)
    
    print("--- Starting Live JD Parsing Verification ---")
    
    for i, jd_text in enumerate(JDS):
        print(f"\nProcessing JD #{i+1}...")
        try:
            job = service.process_raw_jd(jd_text)
            
            print(f"Title: {job.title}")
            print(f"Min Experience: {job.min_experience_years}")
            
            print("\n  MANDATORY REQUIREMENTS:")
            for req in job.mandatory_skills:
                print(f"   - {req.get('canonical_skill_name')} (Type: {req.get('requirement_type')}, Mode: {req.get('evaluation_mode')})")
                print(f"     Evidence: '{req.get('original_text')}'")
                
            print("\n  PREFERRED REQUIREMENTS:")
            for req in job.preferred_skills:
                print(f"   - {req.get('canonical_skill_name')} (Type: {req.get('requirement_type')}, Mode: {req.get('evaluation_mode')})")
                print(f"     Evidence: '{req.get('original_text')}'")
                
        except Exception as e:
            print(f"Error processing JD: {e}")

if __name__ == "__main__":
    run_live_test()

if __name__ == '__main__':
    os.environ['AI_PROVIDER'] = 'openai'
    run_live_test()

