import pytest
from services.search.eligibility import EligibilityEngine, EligibilityStatus
from models.all_models import Candidate, JobRequirement, CandidateSkill

def test_eligibility_minimum_experience():
    job = JobRequirement(min_experience_years=6.0)
    
    # Meets
    c1 = Candidate(id=1, total_experience_years=7.0, skills=[])
    res1 = EligibilityEngine.evaluate(c1, job)
    assert res1.eligible is True
    assert res1.requirements[0].status == EligibilityStatus.MEETS
    
    # Fails
    c2 = Candidate(id=2, total_experience_years=4.0, skills=[])
    res2 = EligibilityEngine.evaluate(c2, job)
    assert res2.eligible is False
    assert res2.requirements[0].status == EligibilityStatus.FAILS

def test_eligibility_mandatory_skills():
    job = JobRequirement(
        mandatory_skills=[
            {
                "canonical_skill_name": "Python",
                "canonical_skill_id": 1,
                "evaluation_mode": "DETERMINISTIC"
            }
        ]
    )
    
    # Missing explicit skill -> FAILS and ineligible
    c1 = Candidate(id=1, skills=[])
    res1 = EligibilityEngine.evaluate(c1, job)
    assert res1.eligible is False
    assert res1.requirements[0].status == EligibilityStatus.FAILS
    
    # Has skill exactly
    c2 = Candidate(id=2, skills=[CandidateSkill(canonical_skill_id=1, original_extracted_skill="Py")])
    res2 = EligibilityEngine.evaluate(c2, job)
    assert res2.eligible is True
    assert res2.requirements[0].status == EligibilityStatus.MEETS

def test_eligibility_mandatory_skills_with_experience():
    job = JobRequirement(
        mandatory_skills=[
            {
                "canonical_skill_name": "Python",
                "canonical_skill_id": 1,
                "evaluation_mode": "DETERMINISTIC",
                "minimum_experience": 5.0
            }
        ]
    )
    
    # Has skill, but insufficient experience -> FAILS
    c1 = Candidate(id=1, skills=[CandidateSkill(canonical_skill_id=1, original_extracted_skill="Py", years_of_experience=3.0)])
    res1 = EligibilityEngine.evaluate(c1, job)
    assert res1.eligible is False
    assert res1.requirements[0].status == EligibilityStatus.FAILS

def test_eligibility_contextual_requirement():
    job = JobRequirement(
        mandatory_skills=[
            {
                "canonical_skill_name": "Fintech",
                "evaluation_mode": "CONTEXTUAL"
            }
        ]
    )
    
    c1 = Candidate(id=1, skills=[])
    res1 = EligibilityEngine.evaluate(c1, job)
    assert res1.eligible is True  # Contextual does not hard fail
    assert res1.requirements[0].status == EligibilityStatus.UNKNOWN
