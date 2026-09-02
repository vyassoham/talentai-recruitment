from sqlalchemy.orm import Session
from models.all_models import IngestionJob, CandidateDocument
from core.database import SessionLocal
from core.storage import LocalStorage
from services.documents.extractor import DocumentExtractor
from services.documents.normalizer import TextNormalizer
from services.ai.cv_parser import CVParser
from services.candidates.candidate_service import CandidateService
from services.ai.embeddings import EmbeddingsService

class IngestionPipeline:
    def __init__(self, job_id: str):
        self.job_id = job_id
        
    def run(self):
        db: Session = SessionLocal()
        try:
            job = db.get(IngestionJob, self.job_id)
            if not job:
                return
                
            job.status = "IN_PROGRESS"
            db.commit()
            
            doc = db.get(CandidateDocument, job.document_id)
            
            # Resume from last failed stage or start from EXTRACTING
            if job.stage in ["UPLOADED", "VALIDATING", "EXTRACTING"]:
                self._transition(db, job, doc, "EXTRACTING")
                extractor = DocumentExtractor(LocalStorage())
                raw_text = extractor.extract_text(doc.storage_key)
                doc.raw_extracted_text = raw_text
                doc.extraction_status = "COMPLETED"
                db.commit()
                
            if job.stage in ["EXTRACTING", "NORMALIZING"]:
                self._transition(db, job, doc, "NORMALIZING")
                normalized = TextNormalizer.normalize(doc.raw_extracted_text)
                doc.normalized_text = normalized
                db.commit()
                
            if job.stage in ["NORMALIZING", "PARSING"]:
                self._transition(db, job, doc, "PARSING")
                parser = CVParser()
                structured = parser.parse_cv(doc.normalized_text)
                
                if not structured.is_valid_resume:
                    reason = structured.validation_reason or "Document does not appear to be a valid Resume/CV"
                    self._transition(db, job, doc, "FAILED", error=reason, status="FAILED")
                    db.delete(doc) # Optionally delete the invalid document to save space
                    db.commit()
                    return
                
                # Keep in memory for next step
                
            if job.stage in ["PARSING", "NORMALIZING_SKILLS", "CALCULATING_EXPERIENCE", "DEDUPLICATING"]:
                # Grouped Candidate DB writes
                self._transition(db, job, doc, "SAVING_CANDIDATE")
                cand_service = CandidateService(db)
                candidate = cand_service.save_structured_candidate(doc.id, structured)
                doc.parsing_status = "COMPLETED"
                db.commit()
                
                # Trigger Phase 6.7: Full Background Enrichment (GitHub + StackOverflow + Scholar + Design)
                from core.queue import queue_client
                from services.enrichment.web_enrichment import run_full_enrichment
                queue_client.enqueue(
                    job_type="ENRICHMENT_FULL",
                    payload={"candidate_id": candidate.id},
                    task_func=run_full_enrichment,
                    candidate_id=candidate.id
                )
                
            if job.stage in ["SAVING_CANDIDATE", "EMBEDDING"]:
                self._transition(db, job, doc, "EMBEDDING")
                EmbeddingsService.generate_candidate_embedding(db, doc.candidate_id)
                doc.embedding_status = "COMPLETED"
                db.commit()
                
            # Done
            self._transition(db, job, doc, "COMPLETED", status="COMPLETED")
            
        except Exception as e:
            db.rollback()
            job = db.get(IngestionJob, self.job_id)
            if job:
                job.status = "FAILED"
                job.error_message = str(e)
                job.error_type = type(e).__name__
                db.commit()
        finally:
            db.close()

    def _transition(self, db, job, doc, new_stage, status="IN_PROGRESS"):
        job.stage = new_stage
        job.status = status
        db.commit()
