from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class RequirementType(str, Enum):
    MANDATORY = "MANDATORY"
    PREFERRED = "PREFERRED"
    OTHER = "OTHER" # e.g. Domain knowledge, soft skills

class EvaluationMode(str, Enum):
    DETERMINISTIC = "DETERMINISTIC" # strict filter
    SEMANTIC = "SEMANTIC" # vector search
    CONTEXTUAL = "CONTEXTUAL" # deep AI re-evaluation

class ParsedRequirement(BaseModel):
    original_text: str
    canonical_skill_name: Optional[str] = None # Will map to ontology ID later
    category: Optional[str] = None # 'Technical', 'Domain', 'Soft Skill'
    requirement_type: RequirementType
    minimum_experience: Optional[float] = None
    maximum_experience: Optional[float] = None
    importance: int = Field(default=5, ge=1, le=10) # 10 is highest
    evaluation_mode: EvaluationMode

class ParsedJobRequirement(BaseModel):
    title: Optional[str] = None
    seniority: Optional[str] = None
    location: Optional[str] = None
    work_arrangement: Optional[str] = None # 'Remote', 'Hybrid', 'On-site'
    total_experience_years: Optional[float] = None
    
    requirements: List[ParsedRequirement] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    domain_requirements: List[str] = Field(default_factory=list)
