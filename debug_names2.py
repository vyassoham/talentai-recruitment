import os
import re
from core.database import SessionLocal
from models.all_models import Candidate, CandidateDocument
from services.ai.provider import get_ai_provider
from pydantic import BaseModel

class ExtractedName(BaseModel):
    correct_name: str

db = SessionLocal()
c = db.query(Candidate).filter(Candidate.name.ilike('%developer%')).first()
doc = db.query(CandidateDocument).filter(CandidateDocument.candidate_id == c.id).first()

text_chunk = doc.raw_extracted_text[:1500] if doc and doc.raw_extracted_text else 'No text'
prompt = f"Extract the REAL name of the candidate from the beginning of this CV. Return ONLY the name.\n\nCV Text:\n{text_chunk}"

provider = get_ai_provider()
try:
    result, _ = provider.generate_structured(prompt, ExtractedName, "You are a precise data extractor.")
    print('RESULT TYPE:', type(result))
    print('RESULT:', result)
except Exception as e:
    print('ERROR:', e)

db.close()
