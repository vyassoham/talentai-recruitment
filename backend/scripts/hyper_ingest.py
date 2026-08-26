import os
import glob
import logging
import re
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.database import SessionLocal
from core.storage import get_storage_provider
from models.all_models import Candidate, CandidateSkill, CandidateDocument
from services.documents.extractor import DocumentExtractor
from services.candidates.skill_normalizer import SkillNormalizer

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

COMMON_SKILLS = [
    "python", "java", "c++", "c#", ".net", "dotnet", "javascript", "typescript", "react", "react.js",
    "node.js", "nodejs", "fastapi", "flask", "django", "sql", "postgresql", "mysql", "mongodb",
    "redis", "docker", "kubernetes", "aws", "azure", "gcp", "devops", "ci/cd", "git", "linux",
    "rest api", "graphql", "html", "css", "tailwind", "next.js", "vue", "angular", "spark",
    "kafka", "airflow", "hadoop", "pandas", "numpy", "pytorch", "tensorflow", "machine learning",
    "ai", "nlp", "llm", "golang", "rust", "php", "ruby", "android", "ios", "swift", "flutter",
    "spring boot", "microservices", "power bi", "tableau", "snowflake", "databricks", "salesforce"
]

def extract_profile_fast(text: str, filename: str):
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    name = None
    if lines:
        for line in lines[:5]:
            clean_l = re.sub(r'[^a-zA-Z\s]', '', line).strip()
            if 2 <= len(clean_l.split()) <= 4 and not any(kw in clean_l.lower() for kw in ['resume', 'curriculum', 'cv', 'page', 'phone', 'email']):
                name = clean_l
                break
    if not name:
        clean_fn = os.path.splitext(filename)[0]
        name = re.sub(r'[^a-zA-Z\s]', ' ', clean_fn).strip()
        if not name:
            name = 'Candidate Profile'

    title = 'Software Engineer'
    title_matches = re.findall(r'(Senior\s+[A-Za-z]+|Lead\s+[A-Za-z]+|[A-Za-z]+\s+Developer|[A-Za-z]+\s+Engineer|Data\s+Scientist|DevOps\s+Engineer|Architect)', text, re.IGNORECASE)
    if title_matches:
        title = title_matches[0].strip().title()

    exp_matches = re.findall(r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+experience', text, re.IGNORECASE)
    if exp_matches:
        try:
            exp_years = float(exp_matches[0])
        except:
            exp_years = 3.5
    else:
        exp_years = 3.0

    lower_text = text.lower()
    found_skills = []
    for s in COMMON_SKILLS:
        pattern = r'\b' + re.escape(s) + r'\b'
        if re.search(pattern, lower_text):
            found_skills.append(s.title())

    return {
        'name': name,
        'title': title,
        'experience': exp_years,
        'skills': list(set(found_skills))
    }

def process_file(fpath):
    fname = os.path.basename(fpath)
    try:
        with open(fpath, 'rb') as f:
            content = f.read()

        if len(content) < 50:
            return False

        file_hash = hashlib.sha256(content).hexdigest()
        storage = get_storage_provider()
        extractor = DocumentExtractor(storage)

        with SessionLocal() as db:
            existing = db.query(CandidateDocument).filter(CandidateDocument.sha256_hash == file_hash).first()
            if existing:
                return 'SKIPPED'

            storage_key = storage.save(content, fname)
            raw_text = extractor.extract_text(storage_key)
            if not raw_text or len(raw_text.strip()) < 30:
                return False

            profile = extract_profile_fast(raw_text, fname)

            cand = Candidate(
                name=profile['name'],
                current_title=profile['title'],
                total_experience_years=profile['experience'],
                embedding=None, # Skip embedding to make it blazing fast!
                source='GOOGLE_DRIVE_BATCH2'
            )
            db.add(cand)
            db.flush()

            doc = CandidateDocument(
                candidate_id=cand.id,
                original_filename=fname,
                storage_key=storage_key,
                mime_type='application/pdf' if fname.endswith('.pdf') else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                file_size=len(content),
                sha256_hash=file_hash,
                raw_extracted_text=raw_text[:5000],
                normalized_text=raw_text[:5000],
                extraction_status='COMPLETED',
                parsing_status='COMPLETED',
                embedding_status='SKIPPED'
            )
            db.add(doc)

            for s in profile['skills']:
                orig, can_id = SkillNormalizer.normalize_skill(db, s)
                cs = CandidateSkill(
                    candidate_id=cand.id,
                    canonical_skill_id=can_id,
                    original_extracted_skill=orig
                )
                db.add(cs)

            db.commit()
            return f"INGESTED {cand.name}"
    except Exception as e:
        logger.error(f"Error on {fname}: {e}")
        return False

def hyper_ingest_all(source_folder=r'D:\recruitment_platform\gdrive_resumes_batch2'):
    patterns = [os.path.join(source_folder, '*.pdf'), os.path.join(source_folder, '*.docx')]
    files = []
    for pat in patterns:
        files.extend(glob.glob(pat))

    logger.info(f"Starting HYPER-INGEST on {len(files)} files...")
    
    ingested = 0
    skipped = 0
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(process_file, f): f for f in files}
        for future in as_completed(futures):
            res = future.result()
            if res == 'SKIPPED':
                skipped += 1
            elif res and res.startswith('INGESTED'):
                ingested += 1
                logger.info(res)
                
    logger.info(f"Finished! Ingested: {ingested}, Skipped: {skipped}")

if __name__ == '__main__':
    hyper_ingest_all()
