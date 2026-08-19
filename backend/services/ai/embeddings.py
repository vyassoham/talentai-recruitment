from sqlalchemy.orm import Session
from models.all_models import Candidate, AIRegistry
from services.ai.provider import get_ai_provider

class EmbeddingsService:
    @staticmethod
    def generate_candidate_embedding(db: Session, candidate_id: int):
        candidate = db.get(Candidate, candidate_id)
        if not candidate:
            return
            
        provider = get_ai_provider()
        
        # Build a rich summary string to embed, rather than the raw CV
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
        
        # Generate and unpack tuple (vector_list, usage_dict)
        vector, usage = provider.generate_embeddings(embed_text)
        candidate.embedding = vector
        
        # Audit
        registry = AIRegistry(
            entity_type="candidate_embedding",
            entity_id=str(candidate.id),
            provider=provider.__class__.__name__,
            model_name=provider.embedding_model_name,
            input_hash=str(hash(embed_text)),
            token_usage=usage
        )
        db.add(registry)
        db.commit()
