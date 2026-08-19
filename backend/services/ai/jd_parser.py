from sqlalchemy.orm import Session
from services.ai.provider import get_ai_provider
from services.ai.audit import AIAuditService
from services.jobs.schemas import ParsedJobRequirement

JD_PARSER_V1 = """
You are an expert technical recruiter AI. Extract job requirements from the provided Job Description into strict JSON.

CRITICAL RULES FOR MANDATORY VS PREFERRED:
1. MANDATORY (requirement_type="MANDATORY"): Only classify a skill as mandatory if the JD explicitly uses words like "Must have", "Required", "Minimum", or if it is the core technology of the role (e.g. "Python Developer" -> Python is mandatory).
2. PREFERRED (requirement_type="PREFERRED"): Classify as preferred if the JD uses words like "Nice to have", "Preferred", "Plus", "Bonus", or "Familiarity with".
3. If the JD DOES NOT mention a skill (e.g., Kubernetes is not in the text), DO NOT INCLUDE IT IN THE JSON. Do not hallucinate requirements.

CRITICAL RULES FOR CLASSIFICATION:
- Technical tools/languages (Python, AWS, React) -> Set category="Technical"
- Industry experience (Fintech, Healthcare) -> Put in `domain_requirements`, not as a technical skill. DO NOT invent a canonical technical skill for a domain.
- Soft skills ("Strong communication") -> Set category="Soft Skill", evaluation_mode="CONTEXTUAL".

For every requirement, the `original_text` MUST be an exact quote or very close paraphrase from the JD.
"""

class JDParser:
    def __init__(self, db: Session):
        self.db = db
        self.provider = get_ai_provider()
        self.pipeline_version = "v1.0"
        self.prompt_version = "JD_PARSER_V1"

    def parse(self, job_id_str: str, raw_jd_text: str) -> ParsedJobRequirement:
        from core.security import SecurityUtils
        safe_jd = SecurityUtils.sanitize_for_llm(raw_jd_text, "job_description")
        
        prompt = f"Extract structured requirements from this Job Description:\n\n{safe_jd}"
        
        def _operation():
            return self.provider.generate_structured(
                prompt=prompt,
                schema_cls=ParsedJobRequirement,
                system_prompt=JD_PARSER_V1
            )
            
        result = AIAuditService.execute_and_audit(
            db=self.db,
            entity_type="job_parsing",
            entity_id=job_id_str,
            operation=_operation,
            provider_name=self.provider.__class__.__name__,
            model_name=self.provider.model_name,
            prompt_version=self.prompt_version,
            pipeline_version=self.pipeline_version,
            input_data=raw_jd_text
        )
        
        return result
