from pydantic import BaseModel, Field
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
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    social_links: Optional[dict] = Field(default_factory=dict, description="Dictionary of platform name to URL, e.g. {'github': 'https://github.com/abc'}")
    
    employment_history: List[ParsedEmployment] = Field(default_factory=list)
    skills: List[ParsedSkill] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)
