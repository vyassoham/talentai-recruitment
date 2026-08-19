from sqlalchemy.orm import Session
from models.all_models import Candidate, CandidateSkill, Employment, CandidateDocument
from services.documents.schemas import StructuredCandidate
from services.candidates.skill_normalizer import SkillNormalizer
from services.candidates.experience import ExperienceCalculator
from services.candidates.deduplication import DeduplicationService

class CandidateService:
    def __init__(self, db: Session):
        self.db = db

    def save_structured_candidate(self, document_id: int, structured_data: StructuredCandidate) -> Candidate:
        document = self.db.get(CandidateDocument, document_id)
        if not document:
            raise ValueError("Document not found")
            
        # 1. Deduplication Check
        candidate = DeduplicationService.find_potential_candidate(
            self.db, email=structured_data.email, phone=structured_data.phone
        )
        
        if not candidate:
            candidate = Candidate(
                name=structured_data.name,
                email=structured_data.email,
                phone=structured_data.phone,
                location=structured_data.location,
                social_links=structured_data.social_links,
                source="UPLOAD"
            )
            self.db.add(candidate)
            self.db.flush() # get ID
        else:
            if structured_data.social_links:
                candidate.social_links = structured_data.social_links
                self.db.flush()
                
        # Link document
        document.candidate_id = candidate.id
        
        # 2. Employment & Experience
        candidate.total_experience_years = ExperienceCalculator.calculate_total_experience(structured_data.employment_history)
        
        for emp_data in structured_data.employment_history:
            emp = Employment(
                candidate_id=candidate.id,
                company=emp_data.company,
                job_title=emp_data.title,
                start_date=ExperienceCalculator._parse_date(emp_data.start_date),
                end_date=ExperienceCalculator._parse_date(emp_data.end_date),
                description=emp_data.description,
                extracted_skills=emp_data.skills
            )
            self.db.add(emp)
            
            # Update current
            if not emp_data.end_date or emp_data.end_date.lower() in ['present', 'current']:
                candidate.current_company = emp_data.company
                candidate.current_title = emp_data.title
                
        # 3. Skills Normalization
        for skill_data in structured_data.skills:
            orig, can_id = SkillNormalizer.normalize_skill(self.db, skill_data.original_name)
            skill = CandidateSkill(
                candidate_id=candidate.id,
                canonical_skill_id=can_id,
                original_extracted_skill=orig,
                category=skill_data.category,
                evidence_references={"evidence": skill_data.evidence} if skill_data.evidence else None,
                years_of_experience=skill_data.years_of_experience,
                confidence=skill_data.confidence
            )
            self.db.add(skill)
            
        self.db.commit()
        return candidate
