import re
import string
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class QuoteValidationItem(BaseModel):
    quote: str = Field(description="The exact quote or claim being verified.")
    is_supported: bool = Field(description="True if the claim is directly supported, mentioned, or reasonably paraphrased in the source text. False if it is hallucinated, fabricated, or contradicts the source.")
    explanation: str = Field(default="", description="Concise explanation of why it is supported or hallucinated.")

class BatchValidationResult(BaseModel):
    validations: List[QuoteValidationItem] = Field(default_factory=list)

LLM_JUDGE_SYSTEM_PROMPT = """You are an impartial, highly accurate Technical Recruitment Auditor and Hallucination Checker.
Your task is to independently verify whether specific claims or evidence quotes extracted about a candidate are genuinely grounded in and supported by their resume or external evidence.

CRITICAL EVALUATION RULES:
1. SUPPORTED (is_supported=true):
   - The claim is explicitly stated, or is a reasonable paraphrase, or a direct logical implication of what is described in the resume or external evidence.
   - Examples of SUPPORTED (PASS):
     * CV: 'Built servers for 5 years' -> Claim: '5 years backend experience' => SUPPORTED
     * CV: 'Developed React frontend apps with Tailwind' -> Claim: 'Experience building modern React user interfaces' => SUPPORTED
     * CV: 'Architected PostgreSQL schemas with pgvector' -> Claim: 'Vector database and SQL optimization expertise' => SUPPORTED
     * CV: 'Managed 4 engineers and ran sprint planning' -> Claim: 'Team leadership and agile scrum experience' => SUPPORTED

2. HALLUCINATED / FABRICATED (is_supported=false):
   - The claim asserts a major skill, framework, role, or number of years NEVER mentioned or heavily exaggerated/contradicted by the resume.
   - Examples of NOT SUPPORTED (FAIL):
     * CV only mentions HTML and CSS -> Claim: '10 years Kubernetes and Golang distributed systems' => NOT SUPPORTED
     * CV: 'Junior developer for 6 months' -> Claim: 'Led 100+ engineers as VP of Engineering' => NOT SUPPORTED
     * CV has no mention of AWS -> Claim: 'AWS Certified Solutions Architect' => NOT SUPPORTED

Output strictly valid JSON conforming to the requested schema.
"""

class EvidenceValidator:
    """
    Independently verifies that the evidence quotes provided by the AI 
    actually exist or are semantically grounded in the source document (CV text).
    
    Uses a high-performance 2-tier architecture:
    1. Tier 1 (Fast-Path): Deterministic exact substring matching after punctuation normalization (0 latency, 0 tokens).
    2. Tier 2 (LLM-as-a-Judge): Semantic verification using an LLM to evaluate paraphrases and catch true hallucinations.
    3. Resilient Fallback: Jaccard word-overlap heuristic if LLM provider is offline or unreachable.
    """
    
    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Removes punctuation, extra whitespace, and lowercases text
        to allow for robust substring matching.
        """
        if not text:
            return ""
        text = text.lower()
        text = text.translate(str.maketrans('', '', string.punctuation))
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @classmethod
    def validate_quotes(
        cls, 
        source_text: str, 
        external_evidence: str, 
        quotes: List[str],
        provider: Optional[Any] = None,
        penalty_per_hallucination: float = 5.0
    ) -> Dict[str, Any]:
        """
        Validates a list of quotes against the combined source text.
        Returns a dictionary with validation results, hallucination count, and calculated penalty.
        """
        normalized_source = cls._normalize_text(source_text)
        if external_evidence:
            normalized_source += " " + cls._normalize_text(external_evidence)
            
        validation_results: Dict[str, str] = {}
        explanations: Dict[str, str] = {}
        hallucination_count = 0
        unresolved_quotes: List[str] = []
        
        # -------------------------------------------------------------
        # Tier 1: Fast-Path Deterministic Check
        # -------------------------------------------------------------
        for quote in quotes:
            if not quote or quote.strip().lower() in ["none", "n/a", "not mentioned", "not found", "no evidence"]:
                validation_results[quote] = "PASS"
                explanations[quote] = "Standard absence-of-evidence statement"
                continue
                
            norm_quote = cls._normalize_text(quote)
            
            # Exact normalized substring match
            if norm_quote and norm_quote in normalized_source:
                validation_results[quote] = "PASS"
                explanations[quote] = "Direct exact quote match in source document"
            else:
                unresolved_quotes.append(quote)

        # If all quotes passed exact match, return immediately
        if not unresolved_quotes:
            return {
                "results": validation_results,
                "hallucination_count": 0,
                "penalty": 0.0,
                "explanations": explanations
            }

        # -------------------------------------------------------------
        # Tier 2: LLM-as-a-Judge Semantic Evaluation
        # -------------------------------------------------------------
        llm_evaluated: Dict[str, bool] = {}
        
        try:
            # Resolve AI provider if not explicitly injected
            ai_provider = provider
            if ai_provider is None:
                from services.ai.provider import get_ai_provider
                ai_provider = get_ai_provider()
                
            from services.ai.provider import MockProvider
            if ai_provider and not isinstance(ai_provider, MockProvider):
                # Prepare compact source context for prompt
                source_context = (source_text or "")[:10000]
                if external_evidence:
                    source_context += f"\n\n--- EXTERNAL EVIDENCE ---\n{external_evidence[:3000]}"
                    
                quotes_block = "\n".join([f"- \"{q}\"" for q in unresolved_quotes])
                judge_prompt = (
                    f"--- CANDIDATE RESUME & EVIDENCE ---\n{source_context}\n\n"
                    f"--- EVIDENCE QUOTES / CLAIMS TO AUDIT ---\n{quotes_block}\n\n"
                    f"Please audit each claim and determine if it is semantically supported or hallucinated."
                )
                
                judge_result, _ = ai_provider.generate_structured(
                    prompt=judge_prompt,
                    schema_cls=BatchValidationResult,
                    system_prompt=LLM_JUDGE_SYSTEM_PROMPT
                )
                
                if judge_result and getattr(judge_result, "validations", None):
                    for v in judge_result.validations:
                        # Match to unresolved quote (handle minor whitespace variations from LLM response)
                        for uq in unresolved_quotes:
                            if uq == v.quote or cls._normalize_text(uq) == cls._normalize_text(v.quote):
                                llm_evaluated[uq] = v.is_supported
                                explanations[uq] = v.explanation or ("Supported by LLM judge" if v.is_supported else "Flagged as hallucination by LLM judge")
                                break
        except Exception as e:
            logger.warning(f"LLM-as-a-Judge validation encountered an error, falling back to heuristic: {e}")

        # -------------------------------------------------------------
        # Tier 3: Resilient Fallback (Word-Overlap Heuristic)
        # -------------------------------------------------------------
        for quote in unresolved_quotes:
            if quote in llm_evaluated:
                is_supported = llm_evaluated[quote]
                if is_supported:
                    validation_results[quote] = "PASS"
                else:
                    validation_results[quote] = "FAIL"
                    hallucination_count += 1
            else:
                # Heuristic fallback for any quotes not resolved by LLM judge
                norm_quote = cls._normalize_text(quote)
                words = norm_quote.split()
                if len(words) > 3:
                    quote_vocab = set(words)
                    source_vocab = set(normalized_source.split())
                    match_ratio = len(quote_vocab.intersection(source_vocab)) / len(quote_vocab)
                    if match_ratio >= 0.7:
                        validation_results[quote] = "PASS"
                        explanations[quote] = f"Fuzzy word-overlap pass ({match_ratio:.0%} match)"
                        continue
                        
                validation_results[quote] = "FAIL"
                explanations[quote] = "Unverified: claim not supported by source text"
                hallucination_count += 1
                
        # Calculate score penalty (e.g. -5 points per hallucinated quote)
        penalty = hallucination_count * penalty_per_hallucination
        
        return {
            "results": validation_results,
            "hallucination_count": hallucination_count,
            "penalty": penalty,
            "explanations": explanations
        }
