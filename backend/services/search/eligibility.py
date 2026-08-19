from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel
from models.all_models import Candidate, JobRequirement

class EligibilityStatus(str, Enum):
    MEETS = "MEETS"
    FAILS = "FAILS"
    UNKNOWN = "UNKNOWN"
    NOT_EVALUATED = "NOT_EVALUATED"

class RequirementEvaluation(BaseModel):
    requirement: str
    status: EligibilityStatus
    candidate_value: Optional[str] = None
    required_value: Optional[str] = None
    evaluation_mode: str
    reason: str

class CandidateEligibilityResult(BaseModel):
    candidate_id: int
    eligible: bool
    requirements: List[RequirementEvaluation]

class EligibilityEngine:
    @staticmethod
    def evaluate(candidate: Candidate, job: JobRequirement) -> CandidateEligibilityResult:
        """
        Deterministically evaluates if a candidate meets hard constraints.
        Does NOT reject on UNKNOWN or CONTEXTUAL/SEMANTIC requirements.
        """
        evaluations = []
        is_eligible = True
        
        # 1. Evaluate Total Experience Constraint
        if job.min_experience_years is not None:
            c_exp = candidate.total_experience_years or 0.0
            if c_exp >= job.min_experience_years:
                evaluations.append(RequirementEvaluation(
                    requirement="Total Experience",
                    status=EligibilityStatus.MEETS,
                    candidate_value=f"{c_exp} years",
                    required_value=f"{job.min_experience_years} years",
                    evaluation_mode="DETERMINISTIC",
                    reason="Candidate meets minimum total experience."
                ))
            else:
                evaluations.append(RequirementEvaluation(
                    requirement="Total Experience",
                    status=EligibilityStatus.FAILS,
                    candidate_value=f"{c_exp} years",
                    required_value=f"{job.min_experience_years} years",
                    evaluation_mode="DETERMINISTIC",
                    reason="Candidate falls short of minimum total experience."
                ))
                is_eligible = False

        # Prepare candidate skills for fast lookup
        # Map canonical_skill_id -> CandidateSkill object
        c_skills_by_canonical = {
            s.canonical_skill_id: s for s in candidate.skills if s.canonical_skill_id is not None
        }
        
        # We also want to check raw names just in case ontology mapping failed but names match
        c_skills_by_name = {
            s.original_extracted_skill.lower(): s for s in candidate.skills
        }

        # 2. Evaluate Mandatory Skills
        mandatory_reqs = job.mandatory_skills or []
        for req in mandatory_reqs:
            req_name = req.get("canonical_skill_name", "")
            req_id = req.get("canonical_skill_id")
            req_mode = req.get("evaluation_mode", "CONTEXTUAL")
            min_exp = req.get("minimum_experience")
            
            # Non-deterministic requirements default to UNKNOWN, we do not reject
            if req_mode != "DETERMINISTIC":
                evaluations.append(RequirementEvaluation(
                    requirement=req_name,
                    status=EligibilityStatus.UNKNOWN,
                    candidate_value=None,
                    required_value=f"{req_name} (Mode: {req_mode})",
                    evaluation_mode=req_mode,
                    reason="Requirement is not deterministic. Retained for AI evaluation."
                ))
                continue

            # It's DETERMINISTIC. Let's look for it.
            matched_skill = None
            if req_id and req_id in c_skills_by_canonical:
                matched_skill = c_skills_by_canonical[req_id]
            elif req_name.lower() in c_skills_by_name:
                matched_skill = c_skills_by_name[req_name.lower()]

            if matched_skill:
                # We found the skill. Check if there's a specific min_experience for it.
                if min_exp is not None:
                    s_exp = matched_skill.years_of_experience or 0.0
                    if s_exp >= min_exp:
                        evaluations.append(RequirementEvaluation(
                            requirement=req_name,
                            status=EligibilityStatus.MEETS,
                            candidate_value=f"{s_exp} years",
                            required_value=f"{min_exp} years",
                            evaluation_mode="DETERMINISTIC",
                            reason="Candidate possesses skill with required experience."
                        ))
                    else:
                        evaluations.append(RequirementEvaluation(
                            requirement=req_name,
                            status=EligibilityStatus.FAILS,
                            candidate_value=f"{s_exp} years",
                            required_value=f"{min_exp} years",
                            evaluation_mode="DETERMINISTIC",
                            reason="Candidate possesses skill but lacks required experience."
                        ))
                        is_eligible = False
                else:
                    evaluations.append(RequirementEvaluation(
                        requirement=req_name,
                        status=EligibilityStatus.MEETS,
                        candidate_value="Present",
                        required_value="Present",
                        evaluation_mode="DETERMINISTIC",
                        reason="Candidate possesses the mandatory skill."
                    ))
            else:
                # Skill is missing completely in structured data
                # Since evaluation_mode is DETERMINISTIC, a missing skill means FAILS.
                evaluations.append(RequirementEvaluation(
                    requirement=req_name,
                    status=EligibilityStatus.FAILS,
                    candidate_value="Not found in structured data",
                    required_value=req_name,
                    evaluation_mode="DETERMINISTIC",
                    reason="Mandatory deterministic skill not explicitly found in parsed data."
                ))
                is_eligible = False

        return CandidateEligibilityResult(
            candidate_id=candidate.id,
            eligible=is_eligible,
            requirements=evaluations
        )

    @staticmethod
    def filter_eligible_candidates(candidates: List[Candidate], job: JobRequirement) -> List[CandidateEligibilityResult]:
        """Returns only the eligibility results for candidates who did not explicitly FAIL."""
        results = []
        for c in candidates:
            res = EligibilityEngine.evaluate(c, job)
            if res.eligible:
                results.append(res)
        return results
