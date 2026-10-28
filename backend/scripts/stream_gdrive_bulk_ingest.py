import re
import os
import sys
import io
import time
import requests
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Ensure backend directory is in sys.path and backend/.env is loaded
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

env_file = os.path.join(backend_dir, ".env")
if os.path.exists(env_file):
    load_dotenv(env_file, override=True)

from core.database import SessionLocal
from models.all_models import Candidate, CandidateSkill, CandidateDocument, CandidateDemographics
from services.candidates.skill_normalizer import SkillNormalizer
from services.candidates.gender_detector import GenderDetector
from services.ai.provider import MockProvider
from pypdf import PdfReader
from scripts.hyper_ingest import extract_profile_fast

log_file_path = os.path.join(os.path.dirname(__file__), 'gdrive_ingestion.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file_path, encoding='utf-8')
    ]
)
logger = logging.getLogger('BulkIngest')

_OFFLINE_PROVIDER = MockProvider()

SKIP_WORDS = {
    'resume', 'cv', 'curriculum', 'vitae', 'profile', 'summary', 'professional',
    'contact', 'details', 'address', 'education', 'skills', 'experience', 'objective',
    'policy', 'deposit', 'receipt', 'certificate', 'invoice', 'statement', 'salary', 'slip',
    'qualifications', 'career', 'overview', 'page', 'declaration', 'letter', 'date'
}

def is_uuid_or_hash(fn: str) -> bool:
    base = os.path.splitext(fn)[0]
    cleaned = re.sub(r'[^0-9a-fA-F]', '', base)
    return len(cleaned) >= 20 and len(cleaned) / max(len(base), 1) > 0.65

def clean_candidate_name(raw_name: str, filename: str, raw_text: str = '') -> str:
    # 1. First attempt: Top 8 lines of resume text
    if raw_text:
        lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
        for line in lines[:8]:
            l_sub = re.sub(r'^(name\s*of\s*the\s*life\s*assured\s*:|life\s*assured\s*:|name\s*:|full\s*name\s*:|candidate\s*name\s*:)', '', line, flags=re.I).strip()
            l_clean = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '', l_sub)
            l_clean = re.sub(r'\+?\d[\d\s-]{8,15}\d', '', l_clean)
            l_clean = re.sub(r'[^a-zA-Z\s]', ' ', l_clean).strip()
            has_skip = any(w.lower() in SKIP_WORDS for w in l_clean.split())
            if has_skip and not any(re.search(r'\b(name|assured)\b', line, re.I) for _ in [0]):
                continue
            words = [w for w in l_clean.split() if w.lower() not in SKIP_WORDS]
            if 2 <= len(words) <= 4 and all(len(w) >= 2 for w in words):
                return ' '.join(w.capitalize() for w in words)

    # 2. Second attempt: Filename (if not a UUID/hash)
    if not is_uuid_or_hash(filename):
        fn = os.path.splitext(filename)[0]
        if fn.lower().endswith('.docx'):
            fn = fn[:-5]
        fn_clean = re.sub(r'[^a-zA-Z\s]', ' ', fn).strip()
        words = [w for w in fn_clean.split() if w.lower() not in SKIP_WORDS and w.lower() not in [
            'updated', 'latest', 'years', 'developer', 'engineer', 'new', 'final', 'doc', 'pdf',
            'tech', 'lead', 'senior', 'fresher', 'experience', 'yr', 'yrs', 'android', 'ios',
            'python', 'java', 'dev', 'ml', 'qa', 'fullstack', 'frontend', 'backend', 'data'
        ]]
        if 2 <= len(words) <= 3 and all(len(w) >= 2 for w in words):
            return ' '.join(w.capitalize() for w in words)
        elif words:
            return ' '.join(w.capitalize() for w in words[:2])

    return 'Candidate Profile'

def process_single_file(file_info):
    fid, fname = file_info
    url = f"https://drive.google.com/uc?id={fid}&export=download"
    
    try:
        session = requests.Session()
        res = session.get(url, stream=True, timeout=15)
        if res.status_code != 200 or len(res.content) < 500:
            return ('FAILED_DOWNLOAD', fname)
            
        content = res.content
        if b'<!DOCTYPE html>' in content[:200] or b'<html' in content[:200]:
            return ('NOT_PDF', fname)
            
        file_hash = hashlib.sha256(content).hexdigest()
        
        # Check existing hash in DB before parsing
        with SessionLocal() as db:
            if db.query(CandidateDocument.id).filter(CandidateDocument.sha256_hash == file_hash).first():
                return ('ALREADY_EXISTS', fname)
                
        # Extract text via pypdf
        try:
            reader = PdfReader(io.BytesIO(content))
            raw_text = "".join([page.extract_text() or "" for page in reader.pages[:5]])
        except Exception:
            return ('PARSE_ERROR', fname)
            
        if len(raw_text.strip()) < 40:
            return ('EMPTY_TEXT', fname)
            
        profile = extract_profile_fast(raw_text, fname)
        candidate_name = clean_candidate_name(profile['name'], fname, raw_text)
        
        with SessionLocal() as db:
            cand = Candidate(
                name=candidate_name,
                email=profile.get('email'),
                phone=profile.get('phone'),
                current_title=profile.get('title') or 'Software Professional',
                total_experience_years=profile.get('experience') or 3.0,
                source='GOOGLE_DRIVE'
            )
            db.add(cand)
            try:
                db.flush()
            except Exception:
                db.rollback()
                # If unique constraint violated on email, retry without email
                cand = Candidate(
                    name=candidate_name,
                    email=None,
                    phone=profile.get('phone'),
                    current_title=profile.get('title') or 'Software Professional',
                    total_experience_years=profile.get('experience') or 3.0,
                    source='GOOGLE_DRIVE'
                )
                db.add(cand)
                db.flush()
                
            gender = GenderDetector.detect(name=candidate_name, cv_text=raw_text[:2000], provider=_OFFLINE_PROVIDER)
            demo = CandidateDemographics(candidate_id=cand.id, gender=gender)
            db.add(demo)

            # Save raw binary PDF to storage for instant local viewing
            storage_dir = os.path.join(backend_dir, "storage")
            os.makedirs(storage_dir, exist_ok=True)
            pdf_path = os.path.join(storage_dir, f"{file_hash}.pdf")
            if not os.path.exists(pdf_path):
                try:
                    with open(pdf_path, "wb") as pf:
                        pf.write(content)
                except Exception:
                    pass

            doc = CandidateDocument(
                candidate_id=cand.id,
                original_filename=fname,
                storage_key=f"{file_hash}.pdf",
                mime_type='application/pdf',
                file_size=len(content),
                sha256_hash=file_hash,
                raw_extracted_text=raw_text[:5000],
                normalized_text=raw_text[:5000],
                extraction_status='COMPLETED',
                parsing_status='COMPLETED',
                embedding_status='SKIPPED'
            )
            db.add(doc)
            
            for s in profile.get('skills', []):
                try:
                    orig, can_id = SkillNormalizer.normalize_skill(db, s, provider=_OFFLINE_PROVIDER)
                    cs = CandidateSkill(
                        candidate_id=cand.id,
                        canonical_skill_id=can_id,
                        original_extracted_skill=orig
                    )
                    db.add(cs)
                except Exception:
                    pass
            db.commit()
            return ('INGESTED', candidate_name)
    except Exception as e:
        return ('ERROR', str(e))

def run_bulk_stream(max_workers=14):
    log_path = r"C:\Users\dell\.gemini\antigravity\brain\db9911ae-e671-413c-95f9-5d67374ba351\.system_generated\tasks\task-2837.log"
    if not os.path.exists(log_path):
        logger.error(f"Task log not found at {log_path}")
        return

    files = []
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            m = re.search(r"Processing file ([a-zA-Z0-9_-]{33}) (.*\.pdf)", line, re.IGNORECASE)
            if m:
                files.append((m.group(1), m.group(2).strip()))

    total = len(files)
    logger.info(f"=== Starting Fresh Bulk Stream Ingestion for {total} Candidates ===")
    
    ingested = 0
    skipped = 0
    failed = 0
    t0 = time.time()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_single_file, f): f for f in files}
        for idx, fut in enumerate(as_completed(futures), 1):
            try:
                status, name = fut.result()
                if status == 'INGESTED':
                    ingested += 1
                elif status in ('ALREADY_EXISTS', 'SKIPPED'):
                    skipped += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
                
            if idx % 25 == 0 or idx == total:
                elapsed = time.time() - t0
                rate = idx / elapsed if elapsed > 0 else 0
                pct = (idx / total) * 100
                logger.info(f"[{idx}/{total} - {pct:.1f}%] Ingested: {ingested} | Skipped: {skipped} | Failed: {failed} | Speed: {rate:.1f} resumes/s")
                sys.stdout.flush()
                
    logger.info(f"=== COMPLETED: {ingested} Ingested, {skipped} Skipped, {failed} Failed in {time.time()-t0:.1f}s ===")

if __name__ == '__main__':
    run_bulk_stream()
