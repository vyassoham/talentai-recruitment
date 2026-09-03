import logging
from typing import Optional, Any, List, Dict
from sqlalchemy.orm import Session
from models.all_models import Candidate, CandidateSectionEmbedding, AIRegistry
from services.ai.provider import get_ai_provider

logger = logging.getLogger(__name__)

class EmbeddingsService:
    """
    Advanced Multi-Vector Embedding Service.
    Solves the 'Lost in the Middle' retrieval problem by generating:
    1. Global Candidate Embedding: High-level profile summary vector.
    2. Chunked Section Embeddings (ColBERT-style Multi-Vector):
       - Dedicated vectors for SKILLS, SUMMARY, individual EMPLOYMENTS, and OPEN-WEB ENRICHMENT.
    """

    @classmethod
    def chunk_candidate_sections(cls, candidate: Candidate) -> List[Dict[str, str]]:
        """
        Decomposes a candidate into distinct semantic sections for granular vector indexing.
        """
        chunks: List[Dict[str, str]] = []

        # 1. Summary & Headline Chunk
        summary_parts = [f"Candidate: {candidate.name or 'Unknown'}"]
        if candidate.current_title:
            summary_parts.append(f"Title: {candidate.current_title}")
        if candidate.total_experience_years:
            summary_parts.append(f"Experience: {candidate.total_experience_years} years")
        if candidate.location:
            summary_parts.append(f"Location: {candidate.location}")
        if candidate.current_company:
            summary_parts.append(f"Current Company: {candidate.current_company}")
            
        chunks.append({
            "section_type": "SUMMARY",
            "section_title": f"Professional Summary - {candidate.current_title or 'Engineer'}",
            "content_chunk": " | ".join(summary_parts)
        })

        # 2. Dedicated Technical Skills Chunk
        skills = [s.original_extracted_skill for s in candidate.skills if s.original_extracted_skill]
        if skills:
            chunks.append({
                "section_type": "SKILLS",
                "section_title": "Core Technical Skills & Stack",
                "content_chunk": f"Technical Skills & Tooling: {', '.join(skills)}"
            })

        # 3. Individual Employment Role Chunks (One vector per job)
        for emp in (candidate.employments or []):
            role_title = emp.job_title or "Software Professional"
            company = emp.company or "Company"
            
            desc_parts = [f"Role: {role_title} at {company}"]
            if emp.start_date:
                start_str = emp.start_date.strftime("%Y-%m") if hasattr(emp.start_date, "strftime") else str(emp.start_date)
                end_str = emp.end_date.strftime("%Y-%m") if (emp.end_date and hasattr(emp.end_date, "strftime")) else "Present"
                desc_parts.append(f"Timeline: {start_str} to {end_str}")
            if emp.description:
                desc_parts.append(f"Responsibilities & Impact: {emp.description[:1000]}")
            if emp.extracted_skills and isinstance(emp.extracted_skills, list):
                desc_parts.append(f"Used Technologies: {', '.join(emp.extracted_skills)}")
                
            chunks.append({
                "section_type": "EXPERIENCE",
                "section_title": f"{role_title} at {company}",
                "content_chunk": " | ".join(desc_parts)
            })

        # 4. Open-Web Technical Evidence Chunk (GitHub / StackOverflow / Portfolios)
        if candidate.external_evidence:
            chunks.append({
                "section_type": "ENRICHMENT",
                "section_title": "Verified Open-Web Footprint",
                "content_chunk": f"Open-Web Technical Footprint:\n{candidate.external_evidence[:1500]}"
            })

        return chunks

    @classmethod
    def generate_candidate_embedding(cls, db: Session, candidate_id: int, provider: Optional[Any] = None):
        """
        Generates both the global summary embedding and multi-vector section embeddings.
        """
        candidate = db.get(Candidate, candidate_id)
        if not candidate:
            return

        ai_provider = provider or get_ai_provider()
        
        # -------------------------------------------------------------
        # 1. Global Candidate Embedding (Summary Vector)
        # -------------------------------------------------------------
        parts = [f"Candidate: {candidate.name or 'Unknown'}"]
        if candidate.current_title:
            parts.append(f"Title: {candidate.current_title}")
        if candidate.total_experience_years:
            parts.append(f"Experience: {candidate.total_experience_years} years")
            
        skills = [s.original_extracted_skill for s in candidate.skills]
        if skills:
            parts.append(f"Skills: {', '.join(skills)}")
            
        employments = [f"{e.job_title} at {e.company}" for e in candidate.employments]
        if employments:
            parts.append(f"History: {', '.join(employments)}")
            
        embed_text = "\n".join(parts)
        
        try:
            vector, usage = ai_provider.generate_embeddings(embed_text)
            candidate.embedding = vector
            
            # Audit telemetry
            registry = AIRegistry(
                entity_type="candidate_embedding",
                entity_id=str(candidate.id),
                provider=ai_provider.__class__.__name__,
                model_name=getattr(ai_provider, "embedding_model_name", "embedding-model"),
                input_hash=str(hash(embed_text)),
                token_usage=usage
            )
            db.add(registry)
        except Exception as e:
            logger.warning(f"Failed generating global candidate embedding: {e}")

        # -------------------------------------------------------------
        # 2. Multi-Vector Chunked Section Embeddings
        # -------------------------------------------------------------
        try:
            # Clear previous section embeddings to ensure idempotency
            db.query(CandidateSectionEmbedding).filter(
                CandidateSectionEmbedding.candidate_id == candidate_id
            ).delete()

            sections = cls.chunk_candidate_sections(candidate)
            for sec in sections:
                chunk_text = sec["content_chunk"]
                if not chunk_text or len(chunk_text.strip()) < 5:
                    continue
                    
                try:
                    sec_vector, _ = ai_provider.generate_embeddings(chunk_text)
                    if sec_vector:
                        sec_embedding = CandidateSectionEmbedding(
                            candidate_id=candidate.id,
                            section_type=sec["section_type"],
                            section_title=sec["section_title"],
                            content_chunk=chunk_text,
                            embedding=sec_vector
                        )
                        db.add(sec_embedding)
                except Exception as chunk_err:
                    logger.debug(f"Failed generating section embedding for {sec['section_type']}: {chunk_err}")
        except Exception as sec_err:
            logger.warning(f"Error processing section embeddings for candidate {candidate_id}: {sec_err}")

        db.commit()

