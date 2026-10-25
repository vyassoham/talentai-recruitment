import os
import sys
import glob
import logging
import re
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal
from core.storage import get_storage_provider
from models.all_models import Candidate, CandidateSkill, CandidateDocument, CandidateDemographics
from services.documents.extractor import DocumentExtractor
from services.candidates.skill_normalizer import SkillNormalizer
from services.candidates.gender_detector import GenderDetector
from services.ai.provider import MockProvider

_OFFLINE_PROVIDER = MockProvider()

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
PHONE_REGEX = re.compile(r'(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{3,4}[\s-]?\d{3,4}')
NON_DIGIT_REGEX = re.compile(r'\D')

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
            if 2 <= len(clean_l.split()) <= 4 and not any(kw in clean_l.lower() for kw in ['resume', 'curriculum', 'cv', 'page', 'phone', 'email', 'experience', 'career']):
                name = clean_l
                break
    if not name:
        clean_fn = os.path.splitext(filename)[0]
        clean_fn = re.sub(r'[^a-zA-Z\s]', ' ', clean_fn).strip()
        words = clean_fn.split()
        if 2 <= len(words) <= 4:
            name = clean_fn.title()
        else:
            name = words[0].title() if words else 'Candidate Profile'

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

    # Contact info
    header = text[:2500]
    emails = EMAIL_REGEX.findall(header)
    email = emails[0] if emails else None
    
    phone = None
    for p in PHONE_REGEX.findall(header):
        digits = NON_DIGIT_REGEX.sub('', p)
        if 10 <= len(digits) <= 14:
            phone = p.strip()
            break

    return {
        'name': name,
        'title': title,
        'experience': exp_years,
        'skills': list(set(found_skills)),
        'email': email,
        'phone': phone
    }

def process_file(fpath):
    fname = os.path.basename(fpath)
    try:
        with open(fpath, 'rb') as f:
            content = f.read()

        if len(content) < 50:
            return 'TOO_SMALL'

        file_hash = hashlib.sha256(content).hexdigest()
        storage = get_storage_provider()
        extractor = DocumentExtractor(storage)

        storage_key = storage.save(content, fname)
        try:
            raw_text = extractor.extract_text(storage_key)
        except Exception:
            return 'CORRUPT_OR_ENCRYPTED'

        if not raw_text or len(raw_text.strip()) < 30:
            return 'EMPTY_TEXT'

        profile = extract_profile_fast(raw_text, fname)

        with SessionLocal() as db:
            existing = db.query(CandidateDocument.id).filter(CandidateDocument.sha256_hash == file_hash).first()
            if existing:
                return 'SKIPPED'

            # Check if candidate with same email already exists to prevent UniqueViolation
            cand = None
            if profile.get('email'):
                cand = db.query(Candidate).filter(Candidate.email == profile['email']).first()

            is_new_candidate = False
            if not cand:
                cand = Candidate(
                    name=profile['name'],
                    email=profile.get('email'),
                    phone=profile.get('phone'),
                    current_title=profile['title'],
                    total_experience_years=profile['experience'],
                    embedding=None,
                    source='GOOGLE_DRIVE'
                )
                db.add(cand)
                try:
                    db.flush()
                    is_new_candidate = True
                except Exception:
                    db.rollback()
                    # Retry without email if email collided
                    cand = Candidate(
                        name=profile['name'],
                        email=None,
                        phone=profile.get('phone'),
                        current_title=profile['title'],
                        total_experience_years=profile['experience'],
                        embedding=None,
                        source='GOOGLE_DRIVE'
                    )
                    db.add(cand)
                    db.flush()
                    is_new_candidate = True

            if is_new_candidate:
                # Offline fast gender detection (Tier 1 pronouns + Tier 2 name lookup, zero network calls)
                gender = GenderDetector.detect(name=cand.name, cv_text=raw_text[:2000], provider=_OFFLINE_PROVIDER)
                demo = CandidateDemographics(
                    candidate_id=cand.id,
                    gender=gender
                )
                db.add(demo)

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

            try:
                db.commit()
                return f"INGESTED {cand.id}: {cand.name}"
            except Exception as commit_err:
                db.rollback()
                logger.warning(f"Commit collision on {fname}: {commit_err}")
                return f"COLLISION_SKIPPED: {fname}"
    except Exception as e:
        logger.error(f"Process error on {fname}: {e}")
        return f"ERROR: {e}"

def hyper_ingest_all(source_folders=None):
    if source_folders is None:
        source_folders = [
            r'D:\recruitment_platform\gdrive_resumes_batch2',
            r'D:\recruitment_platform\gdrive_resumes'
        ]

    files = []
    for sf in source_folders:
        if os.path.exists(sf):
            for pat in [os.path.join(sf, '*.pdf'), os.path.join(sf, '*.docx')]:
                files.extend(glob.glob(pat))

    logger.info(f"Starting HYPER-INGEST on {len(files)} total files across folders...")
    
    ingested = 0
    skipped = 0
    errors = 0
    
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(process_file, f): f for f in files}
        for idx, future in enumerate(as_completed(futures), 1):
            res = future.result()
            if res == 'SKIPPED':
                skipped += 1
            elif res and res.startswith('INGESTED'):
                ingested += 1
            else:
                errors += 1
                
            if idx % 100 == 0 or idx == len(files):
                logger.info(f"[{idx}/{len(files)}] Progress: {ingested} Ingested, {skipped} Skipped, {errors} Errors/Empty")
                
    logger.info(f"\nFINISHED! Ingested: {ingested}, Skipped: {skipped}, Errors/Empty: {errors}")

if __name__ == '__main__':
    hyper_ingest_all()
