from services.documents.schemas import StructuredCandidate
from services.ai.provider import get_ai_provider

class CVParser:
    def __init__(self):
        self.provider = get_ai_provider()
        self.system_prompt = """
        You are an expert recruitment AI. Extract candidate information from the provided text into the strict JSON schema.
        Rules:
        1. Extract explicit facts only. Do not hallucinate.
        2. Format dates as YYYY-MM where possible, or 'present' if current.
        3. For 'evidence' in skills, provide the exact quote from the CV mentioning it.
        4. If a field is not found, leave it null.
        """

    def parse_cv(self, normalized_text: str) -> StructuredCandidate:
        """
        Parses CV text into a structured Pydantic model using the AI provider.
        """
        from core.security import SecurityUtils
        safe_cv = SecurityUtils.sanitize_for_llm(normalized_text, "candidate_cv")
        
        prompt = f"Candidate CV Text:\n\n{safe_cv}\n\nIMPORTANT: Please explicitly extract any 'social_links' found (like GitHub, GitLab, LinkedIn, StackOverflow, Medium, or Portfolio URLs)."
        
        parsed_result, _usage = self.provider.generate_structured(prompt, StructuredCandidate, self.system_prompt)
        
        return parsed_result
