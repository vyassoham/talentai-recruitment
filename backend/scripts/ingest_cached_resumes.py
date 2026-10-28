import os
import sys
import glob
import io
import time
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pypdf import PdfReader
from dotenv import load_dotenv

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(backend_dir, ".env"), override=True)
sys.path.insert(0, backend_dir)

from core.database import SessionLocal
from models.all_models import Candidate, CandidateDocument, CandidateDemographics, CandidateSkill
from services.candidates.skill_normalizer import SkillNormalizer
from services.candidates.gender_detector import GenderDetector
from services.ai.provider import MockProvider
from scripts.stream_gdrive_bulk_ingest import extract_profile_fast, clean_candidate_name

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DiskIngest")

_OFFLINE_PROVIDER = MockProvider()

def process_file_path(pdf_path: str):
    file_hash = os.path.splitext(os.path.basename(pdf_path))[0]
    
    try:
        with open(pdf_path, "rb") as f:
            content = f.read()
            
        if len(content) < 500:
            return ("TOO_SMALL", pdf_path)
            
        try:
            reader = PdfReader(io.BytesIO(content))
            raw_text = "".join([page.extract_text() or "" for page in reader.pages[:5]])
        except Exception:
            return ("PARSE_ERROR", pdf_path)
            
        if len(raw_text.strip()) < 40:
            return ("EMPTY_TEXT", pdf_path)
            
        profile = extract_profile_fast(raw_text, f"{file_hash}.pdf")
        candidate_name = clean_candidate_name(profile.get("name", ""), f"{file_hash}.pdf", raw_text)
        
        with SessionLocal() as db:
            # Re-check hash inside session
            if db.query(CandidateDocument.id).filter(CandidateDocument.sha256_hash == file_hash).first():
                return ("EXISTS", candidate_name)
                
            cand = Candidate(
                name=candidate_name,
                email=profile.get("email"),
                phone=profile.get("phone"),
                current_title=profile.get("title") or "Software Professional",
                total_experience_years=profile.get("experience") or 3.0,
                source="LOCAL_DISK_CACHE"
            )
            db.add(cand)
            try:
                db.flush()
            except Exception:
                db.rollback()
                cand = Candidate(
                    name=candidate_name,
                    email=None,
                    phone=profile.get("phone"),
                    current_title=profile.get("title") or "Software Professional",
                    total_experience_years=profile.get("experience") or 3.0,
                    source="LOCAL_DISK_CACHE"
                )
                db.add(cand)
                db.flush()
                
            gender = GenderDetector.detect(name=candidate_name, cv_text=raw_text[:2000], provider=_OFFLINE_PROVIDER)
            demo = CandidateDemographics(candidate_id=cand.id, gender=gender)
            db.add(demo)
            
            doc = CandidateDocument(
                candidate_id=cand.id,
                original_filename=f"{file_hash}.pdf",
                storage_key=f"{file_hash}.pdf",
                mime_type="application/pdf",
                file_size=len(content),
                sha256_hash=file_hash,
                raw_extracted_text=raw_text[:5000],
                normalized_text=raw_text[:5000],
                extraction_status="COMPLETED",
                parsing_status="COMPLETED",
                embedding_status="SKIPPED"
            )
            db.add(doc)
            
            for s in profile.get("skills", []):
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
            return ("INGESTED", candidate_name)
    except Exception as e:
        return ("ERROR", str(e))

def run_cached_ingest(max_workers=10):
    storage_dir = os.path.join(backend_dir, "storage")
    all_pdfs = glob.glob(os.path.join(storage_dir, "*.pdf"))
    logger.info(f"Scanning storage directory: found {len(all_pdfs)} cached PDFs")
    
    with SessionLocal() as db:
        existing_hashes = {r[0] for r in db.query(CandidateDocument.sha256_hash).all()}
    logger.info(f"Existing documents in DB: {len(existing_hashes)}")
    
    to_process = [p for p in all_pdfs if os.path.splitext(os.path.basename(p))[0] not in existing_hashes]
    total = len(to_process)
    logger.info(f"Target PDFs to ingest: {total}")
    
    if total == 0:
        logger.info("All disk PDFs already exist in database!")
        return
        
    ingested = 0
    skipped = 0
    failed = 0
    t0 = time.time()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_file_path, p): p for p in to_process}
        for idx, fut in enumerate(as_completed(futures), 1):
            try:
                status, name = fut.result()
                if status == "INGESTED":
                    ingested += 1
                elif status in ("EXISTS", "TOO_SMALL", "EMPTY_TEXT"):
                    skipped += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
                
            if idx % 50 == 0 or idx == total:
                elapsed = time.time() - t0
                rate = idx / elapsed if elapsed > 0 else 0
                pct = (idx / total) * 100
                logger.info(f"[{idx}/{total} - {pct:.1f}%] Ingested: {ingested} | Skipped: {skipped} | Failed: {failed} | Speed: {rate:.1f} resumes/s")
                sys.stdout.flush()
                
    logger.info(f"=== COMPLETED CACHED INGESTION: {ingested} Ingested, {skipped} Skipped, {failed} Failed in {time.time()-t0:.1f}s ===")

if __name__ == "__main__":
    run_cached_ingest(max_workers=10)
