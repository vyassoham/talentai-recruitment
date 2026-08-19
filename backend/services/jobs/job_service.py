from sqlalchemy.orm import Session
from models.all_models import JobRequirement
from services.ai.jd_parser import JDParser
from services.jobs.schemas import ParsedJobRequirement
from services.candidates.skill_normalizer import SkillNormalizer
from services.ai.provider import get_ai_provider
from services.ai.audit import AIAuditService
import json

class JobService:
    def __init__(self, db: Session):
        self.db = db
        self.provider = get_ai_provider()

    def process_raw_jd(self, raw_description: str) -> JobRequirement:
        # Create initial DB record
        job = JobRequirement(raw_description=raw_description)
        self.db.add(job)
        self.db.flush()
        
        job_id_str = str(job.id)
        
        # 1. Parse JD
        parser = JDParser(self.db)
        parsed_jd: ParsedJobRequirement = parser.parse(job_id_str, raw_description)
        
        # 2. Ontology Normalization & Segregation
        mandatory = []
        preferred = []
        
        for req in parsed_jd.requirements:
            # Context-aware normalization: we normalize to canonical IDs but keep original terms
            # The JD requires "5+ years React" -> React is the canonical skill
            if req.canonical_skill_name:
                orig, canonical_id = SkillNormalizer.normalize_skill(self.db, req.canonical_skill_name)
                req_dict = req.model_dump()
                req_dict["canonical_skill_id"] = canonical_id
                
                if req.requirement_type == "MANDATORY":
                    mandatory.append(req_dict)
                elif req.requirement_type == "PREFERRED":
                    preferred.append(req_dict)
                    
        # Update DB Model
        job.title = parsed_jd.title
        job.min_experience_years = parsed_jd.total_experience_years
        job.location_requirements = parsed_jd.location
        job.mandatory_skills = mandatory
        job.preferred_skills = preferred
        
        # 3. Job Embedding
        # Create a rich representation for embedding
        embed_parts = [
            f"Title: {job.title}",
            f"Experience required: {job.min_experience_years} years",
            f"Mandatory: {', '.join(r.get('canonical_skill_name') for r in mandatory)}",
            f"Preferred: {', '.join(r.get('canonical_skill_name') for r in preferred)}",
            f"Domain: {', '.join(parsed_jd.domain_requirements)}"
        ]
        embed_text = "\n".join(embed_parts)
        
        def _embed_op():
            return self.provider.generate_embeddings(embed_text)
            
        embedding_vector = AIAuditService.execute_and_audit(
            db=self.db,
            entity_type="job_embedding",
            entity_id=job_id_str,
            operation=_embed_op,
            provider_name=self.provider.__class__.__name__,
            model_name=self.provider.embedding_model_name,
            prompt_version="v1",
            pipeline_version="v1.0",
            input_data=embed_text
        )
        
        job.embedding = embedding_vector
        self.db.commit()
        
        return job

def background_process_jd(job_id: str, raw_description: str):
    from core.database import SessionLocal
    with SessionLocal() as db:
        try:
            service = JobService(db)
            job = service.process_raw_jd(raw_description)
            return {
                "job_id": job.id,
                "title": job.title,
                "status": "COMPLETED"
            }
        except Exception as e:
            # We want to throw so the queue catches it and marks as FAILED
            raise e
