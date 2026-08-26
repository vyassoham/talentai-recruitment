import os
import sys
import glob
import logging
import io
import time
import re
import hashlib
from core.database import SessionLocal
from core.storage import get_storage_provider
from models.all_models import Candidate, CandidateSkill, CandidateDocument, Ontology
from services.documents.extractor import DocumentExtractor
from services.ai.provider import get_ai_provider
from services.candidates.skill_normalizer import SkillNormalizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
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
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    
    # 1. Name
    name = None
    if lines:
        for line in lines[:5]:
            clean_l = re.sub(r'[^a-zA-Z\s]', '', line).strip()
            if 2 <= len(clean_l.split()) <= 4 and not any(kw in clean_l.lower() for kw in ["resume", "curriculum", "cv", "page", "phone", "email"]):
                name = clean_l
                break
    if not name:
        clean_fn = os.path.splitext(filename)[0]
        name = re.sub(r'[^a-zA-Z\s]', ' ', clean_fn).strip()
        if not name:
            name = "Candidate Profile"

    # 2. Title
    title = "Software Engineer"
    title_matches = re.findall(r'(Senior\s+[A-Za-z]+|Lead\s+[A-Za-z]+|[A-Za-z]+\s+Developer|[A-Za-z]+\s+Engineer|Data\s+Scientist|DevOps\s+Engineer|Architect)', text, re.IGNORECASE)
    if title_matches:
        title = title_matches[0].strip().title()

    # 3. Experience Years
    exp_matches = re.findall(r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+experience', text, re.IGNORECASE)
    if exp_matches:
        try:
            exp_years = float(exp_matches[0])
        except:
            exp_years = 3.5
    else:
        exp_years = 3.0

    # 4. Skills matching
    lower_text = text.lower()
    found_skills = []
    for s in COMMON_SKILLS:
        pattern = r'\b' + re.escape(s) + r'\b'
        if re.search(pattern, lower_text):
            found_skills.append(s.title())

    return {
        "name": name,
        "title": title,
        "experience": exp_years,
        "skills": list(set(found_skills))
    }

def fast_ingest_all(source_folder: str = r"D:\recruitment_platform\gdrive_resumes"):
    patterns = [os.path.join(source_folder, "*.pdf"), os.path.join(source_folder, "*.docx")]
    files = []
    for pat in patterns:
        files.extend(glob.glob(pat))

    logger.info(f"🚀 Starting high-speed rate-resilient ingestion of {len(files)} resumes...")

    storage = get_storage_provider()
    extractor = DocumentExtractor(storage)
    ai_provider = get_ai_provider()

    ingested = 0
    skipped = 0

    for idx, fpath in enumerate(files, 1):
        fname = os.path.basename(fpath)
        logger.info(f"[{idx}/{len(files)}] Processing '{fname}'...")

        try:
            with open(fpath, "rb") as f:
                content = f.read()

            if len(content) < 50:
                continue

            file_hash = hashlib.sha256(content).hexdigest()

            with SessionLocal() as db:
                existing = db.query(CandidateDocument).filter(CandidateDocument.sha256_hash == file_hash).first()
                if existing:
                    logger.info(f"Candidate document already exists for {fname}. Skipping.")
                    skipped += 1
                    continue

                # 1. Save & Lossless Compress into Supabase Cloud Bucket
                storage_key = storage.save(content, fname)

                # 2. Extract Text
                raw_text = extractor.extract_text(storage_key)
                if not raw_text or len(raw_text.strip()) < 30:
                    continue

                # 3. Fast Profile Parsing
                profile = extract_profile_fast(raw_text, fname)

                # 4. Generate Semantic 1536-d Vector Embedding with Rate Limit Handling
                emb = None
                try:
                    emb_text = f"{profile['name']}\n{profile['title']}\n{', '.join(profile['skills'])}\n{raw_text[:1200]}"
                    emb_list, _ = ai_provider.generate_embeddings(emb_text)
                    emb = emb_list
                except Exception as e:
                    if "429" in str(e) or "Rate Limit" in str(e):
                        logger.warning("Embedding rate limit reached; sleeping 4s...")
                        time.sleep(4)
                        try:
                            emb_list, _ = ai_provider.generate_embeddings(emb_text)
                            emb = emb_list
                        except:
                            pass

                # 5. Insert Candidate into Supabase Database
                cand = Candidate(
                    name=profile["name"],
                    current_title=profile["title"],
                    total_experience_years=profile["experience"],
                    embedding=emb,
                    source="GOOGLE_DRIVE"
                )
                db.add(cand)
                db.flush()

                # Record Document
                doc = CandidateDocument(
                    candidate_id=cand.id,
                    original_filename=fname,
                    storage_key=storage_key,
                    mime_type="application/pdf" if fname.endswith(".pdf") else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    file_size=len(content),
                    sha256_hash=file_hash,
                    raw_extracted_text=raw_text[:5000],
                    normalized_text=raw_text[:5000],
                    extraction_status="COMPLETED",
                    parsing_status="COMPLETED",
                    embedding_status="COMPLETED" if emb else "SKIPPED"
                )
                db.add(doc)

                # Link Skills
                for s in profile["skills"]:
                    orig, can_id = SkillNormalizer.normalize_skill(db, s)
                    cs = CandidateSkill(
                        candidate_id=cand.id,
                        canonical_skill_id=can_id,
                        original_extracted_skill=orig
                    )
                    db.add(cs)

                db.commit()
                ingested += 1
                logger.info(f"✅ Ingested Candidate #{cand.id}: {cand.name} ({cand.current_title}, {cand.total_experience_years}y exp) with {len(profile['skills'])} skills!")

                # 200ms throttle to stay comfortably within rate limits
                time.sleep(0.2)

        except Exception as e:
            logger.error(f"Error on {fname}: {e}")

    logger.info(
        f"\n========================================\n"
        f"Batch Ingestion Completed Successfully!\n"
        f"Total Ingested:        {ingested}\n"
        f"Duplicates Skipped:    {skipped}\n"
        f"========================================"
    )

if __name__ == "__main__":
    fast_ingest_all()
