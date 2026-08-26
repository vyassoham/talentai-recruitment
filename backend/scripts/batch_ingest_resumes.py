import os
import sys
import glob
import logging
from core.database import SessionLocal
from core.storage import get_storage_provider
from models.all_models import Candidate, CandidateSkill, CandidateDocument, Ontology
from services.documents.extractor import DocumentExtractor
from services.documents.validator import DocumentValidator
from services.documents.optimizer import DocumentOptimizer
from services.ai.cv_parser import CVParser
from services.ai.provider import get_ai_provider
from services.candidates.skill_normalizer import SkillNormalizer
from services.candidates.experience import ExperienceCalculator

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def run_batch_ingestion(source_folder: str = r"D:\recruitment_platform\gdrive_resumes", max_files: int = 500):
    """
    Batch ingests downloaded candidate resumes into Supabase Storage and PostgreSQL database.
    Applies lossless stream compression, AI text extraction, skill normalization, and vector embeddings.
    """
    if not os.path.exists(source_folder):
        logger.error(f"Source folder not found: {source_folder}")
        return

    # Find all PDFs and DOCX files
    patterns = [os.path.join(source_folder, "**", "*.pdf"), os.path.join(source_folder, "**", "*.docx")]
    all_files = []
    for pat in patterns:
        all_files.extend(glob.glob(pat, recursive=True))

    logger.info(f"Found {len(all_files)} resume files in {source_folder}. Processing up to {max_files} files...")

    storage = get_storage_provider()
    extractor = DocumentExtractor(storage)
    parser = CVParser()
    ai_provider = get_ai_provider()

    ingested_count = 0
    skipped_duplicates = 0
    failed_count = 0

    for idx, file_path in enumerate(all_files[:max_files], 1):
        filename = os.path.basename(file_path)
        logger.info(f"[{idx}/{min(len(all_files), max_files)}] Processing '{filename}'...")

        try:
            with open(file_path, "rb") as f:
                content = f.read()

            if len(content) < 100:
                logger.warning(f"File '{filename}' is empty or corrupt. Skipping.")
                failed_count += 1
                continue

            # 1. Antivirus & Document Validation
            is_valid, validation_msg = DocumentValidator.validate(content, filename)
            if not is_valid:
                logger.warning(f"Validation failed for '{filename}': {validation_msg}")
                failed_count += 1
                continue

            # 2. Upload to Supabase Storage with Lossless Compression
            storage_key = storage.save(content, filename)

            # 3. Check for duplicates in DB by storage_key (SHA-256)
            with SessionLocal() as db:
                existing_doc = db.query(CandidateDocument).filter(CandidateDocument.storage_key == storage_key).first()
                if existing_doc:
                    logger.info(f"Duplicate resume detected for '{filename}' ({storage_key}). Skipping DB insert.")
                    skipped_duplicates += 1
                    continue

                # 4. Extract Text
                raw_text = extractor.extract_text(storage_key)
                if not raw_text or len(raw_text.strip()) < 50:
                    logger.warning(f"Insufficient text extracted from '{filename}'.")
                    failed_count += 1
                    continue

                # 5. AI Profile Parsing (Name, Skills, Experience)
                parsed_profile = parser.parse_cv(raw_text)

                # Calculate experience
                exp_records = [{"start_date": emp.start_date, "end_date": emp.end_date} for emp in parsed_profile.employment_history]
                total_exp = ExperienceCalculator.calculate_total_experience(exp_records) if exp_records else 3.0

                # Skills list
                extracted_skills = [s.original_name for s in parsed_profile.skills if s.original_name]

                # 6. Generate 1536-d Vector Embedding
                embedding = None
                try:
                    primary_title = parsed_profile.employment_history[0].title if parsed_profile.employment_history else "Engineering Professional"
                    emb_text = f"{parsed_profile.name or ''}\n{primary_title}\n{', '.join(extracted_skills)}\n{raw_text[:1500]}"
                    emb_list, _ = ai_provider.generate_embeddings(emb_text)
                    embedding = emb_list
                except Exception as e:
                    logger.warning(f"AI embedding generation notice: {e}")

                # 7. Create Candidate in Supabase Database
                clean_name = parsed_profile.name or filename.replace(".pdf", "").replace(".docx", "").replace("_", " ").strip()
                primary_title = parsed_profile.employment_history[0].title if parsed_profile.employment_history else "Engineering Professional"
                primary_company = parsed_profile.employment_history[0].company if parsed_profile.employment_history else None

                candidate = Candidate(
                    name=clean_name,
                    email=parsed_profile.email,
                    phone=parsed_profile.phone,
                    location=parsed_profile.location,
                    current_title=primary_title,
                    current_company=primary_company,
                    total_experience_years=total_exp or 3.0,
                    raw_cv_text=raw_text[:10000],
                    social_links=parsed_profile.social_links or {},
                    embedding=embedding,
                    source="GOOGLE_DRIVE_BATCH"
                )
                db.add(candidate)
                db.flush()

                # Record Document
                doc = CandidateDocument(
                    candidate_id=candidate.id,
                    storage_key=storage_key,
                    file_name=filename,
                    file_size_bytes=len(content)
                )
                db.add(doc)

                # Normalize & Link Skills
                for skill_name in extracted_skills:
                    if skill_name and len(skill_name.strip()) > 1:
                        orig_text, can_id = SkillNormalizer.normalize_skill(db, skill_name.strip())
                        cand_skill = CandidateSkill(
                            candidate_id=candidate.id,
                            canonical_skill_id=can_id,
                            original_extracted_skill=orig_text
                        )
                        db.add(cand_skill)

                db.commit()
                ingested_count += 1
                logger.info(f"Successfully ingested candidate #{candidate.id}: '{candidate.name}' ({primary_title}, {total_exp} Yrs Exp) with {len(extracted_skills)} skills.")

        except Exception as e:
            logger.error(f"Failed to ingest '{filename}': {e}")
            failed_count += 1

    logger.info(
        f"\n========================================\n"
        f"Batch Ingestion Completed!\n"
        f"Successfully Ingested: {ingested_count} Candidates\n"
        f"Skipped Duplicates:    {skipped_duplicates}\n"
        f"Failed/Corrupt Files:  {failed_count}\n"
        f"========================================"
    )

if __name__ == "__main__":
    run_batch_ingestion()
