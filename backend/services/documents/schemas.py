from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Any
from datetime import date

class ParsedSkill(BaseModel):
    original_name: str
    category: Optional[str] = None
    years_of_experience: Optional[float] = None
    last_used: Optional[str] = None # e.g. "2023" or "2023-05"
    evidence: Optional[str] = None
    confidence: Optional[float] = None

class ParsedEmployment(BaseModel):
    company: str
    title: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None # 'present' if current
    description: Optional[str] = None
    skills: List[str] = Field(default_factory=list)

class StructuredCandidate(BaseModel):
    is_valid_resume: bool = Field(description="MUST BE EVALUATED: Set to false ONLY IF the document is clearly not a resume/CV (e.g. an image, a random text file, or unsupported document). Set to true if it is a CV.")
    validation_reason: Optional[str] = Field(default=None, description="If is_valid_resume is false, explain why.")
    name: Optional[str] = Field(default=None, description="Candidate's full name (e.g. 'John Doe'). Cannot be a generic placeholder like 'Resume' or 'Unknown'.")
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    social_links: Optional[dict] = Field(default_factory=dict, description="Dictionary of platform name to URL, e.g. {'github': 'https://github.com/abc'}")
    
    employment_history: List[ParsedEmployment] = Field(default_factory=list)
    skills: List[ParsedSkill] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_candidate_integrity(self) -> "StructuredCandidate":
        from services.documents.validator import DocumentValidator
        
        # 1. If AI already marked it as not a valid resume, ensure reason is set
        if not self.is_valid_resume:
            if not self.validation_reason:
                self.validation_reason = "Document does not appear to be a valid Resume/CV"
            return self

        # 2. Name validation: A valid resume must have an identifiable candidate name
        is_name_valid, name_reason = DocumentValidator.validate_candidate_name(self.name)
        if not is_name_valid:
            self.is_valid_resume = False
            self.validation_reason = f"Invalid candidate name: {name_reason}"
            return self

        # 3. Clean the candidate name
        self.name = DocumentValidator.clean_candidate_name(self.name)

        # 4. Content sanity check: must contain at least skills, employment, or contact info
        has_skills = bool(self.skills and len(self.skills) > 0)
        has_employment = bool(self.employment_history and len(self.employment_history) > 0)
        has_contact = bool(self.email or self.phone)
        
        if not (has_skills or has_employment or has_contact):
            self.is_valid_resume = False
            self.validation_reason = "Document contains no extractable skills, employment history, or contact details"

        return self

