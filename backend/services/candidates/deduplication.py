from sqlalchemy.orm import Session
from models.all_models import CandidateDocument, Candidate

class DeduplicationService:
    @staticmethod
    def check_duplicate_document(db: Session, sha256_hash: str) -> bool:
        """Returns True if the exact file has been uploaded before."""
        return db.query(CandidateDocument).filter(CandidateDocument.sha256_hash == sha256_hash).first() is not None

    @staticmethod
    def find_potential_candidate(db: Session, email: str = None, phone: str = None) -> Candidate:
        """Finds existing candidate by strict identifiers."""
        if email:
            c = db.query(Candidate).filter(Candidate.email == email).first()
            if c: return c
        if phone:
            c = db.query(Candidate).filter(Candidate.phone == phone).first()
            if c: return c
        return None
