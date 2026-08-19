from sqlalchemy.orm import Session
from models.all_models import Ontology
from typing import Tuple, Optional

class SkillNormalizer:
    @staticmethod
    def normalize_skill(db: Session, raw_skill_name: str) -> Tuple[str, Optional[int]]:
        """
        Attempts to map a raw skill name to a canonical skill in the ontology.
        Returns (original_skill, canonical_skill_id).
        Does NOT over-normalize distinct technologies (e.g., Python != Django).
        """
        if not raw_skill_name:
            return raw_skill_name, None
            
        clean_name = raw_skill_name.strip().lower()
        
        # Exact match
        canonical = db.query(Ontology).filter(Ontology.canonical_name.ilike(clean_name)).first()
        if canonical:
            return raw_skill_name, canonical.id
            
        # Alias match (in postgres we'd use jsonb @>, here we'll do a simple iteration for MVP)
        ontologies = db.query(Ontology).all()
        for ont in ontologies:
            if ont.aliases and any(a.lower() == clean_name for a in ont.aliases):
                return raw_skill_name, ont.id
                
        # If not found, we keep it but don't link to ontology
        return raw_skill_name, None
