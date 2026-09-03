import pytest
from services.ai.validator import EvidenceValidator, BatchValidationResult, QuoteValidationItem
from services.ai.provider import MockProvider

def test_evidence_validator_exact_match():
    cv = "Experienced Python developer with 5 years in Django."
    quotes = ["Experienced Python developer", "5 years in Django"]
    
    result = EvidenceValidator.validate_quotes(cv, "", quotes)
    assert result["hallucination_count"] == 0
    assert result["penalty"] == 0.0
    assert all(res == "PASS" for res in result["results"].values())

def test_evidence_validator_fuzzy_match():
    cv = "Experienced   Python\n developer. with 5 years in Django!"
    quotes = ["Experienced Python developer", "5 years in django"]
    
    result = EvidenceValidator.validate_quotes(cv, "", quotes)
    assert result["hallucination_count"] == 0
    assert result["penalty"] == 0.0
    
def test_evidence_validator_hallucination():
    cv = "Experienced Python developer."
    quotes = ["Experienced Python developer", "10 years of Kubernetes experience"]
    
    result = EvidenceValidator.validate_quotes(cv, "", quotes, provider=MockProvider(), penalty_per_hallucination=5.0)
    assert result["hallucination_count"] == 1
    assert result["penalty"] == 5.0
    assert result["results"]["10 years of Kubernetes experience"] == "FAIL"

def test_evidence_validator_ignores_none():
    cv = "Experienced Python developer."
    quotes = ["None", "N/A", "Not mentioned"]
    
    result = EvidenceValidator.validate_quotes(cv, "", quotes)
    assert result["hallucination_count"] == 0
    assert result["penalty"] == 0.0

def test_evidence_validator_partial_chunk():
    cv = "Led the migration of the backend monolith to AWS microservices."
    # The LLM slightly misquoted, adding "architecture" at the end, but the chunk is mostly there
    quotes = ["Led the migration of the backend monolith to AWS microservices architecture."]
    
    result = EvidenceValidator.validate_quotes(cv, "", quotes, provider=MockProvider())
    assert result["hallucination_count"] == 0

def test_evidence_validator_llm_judge_semantic_paraphrase():
    """
    Tests that a semantic paraphrase (e.g. 'Built servers for 5 years' vs '5 years backend experience')
    is correctly validated as PASS by the LLM-as-a-Judge provider mock.
    """
    cv = "Built scalable distributed servers for 5 years using Python."
    # Paraphrased quote that does not share exact substring or consecutive words
    quotes = ["5 years of robust backend engineering experience"]
    
    class MockJudgeProvider:
        model_name = "mock-judge"
        def generate_structured(self, prompt, schema_cls, system_prompt=""):
            return BatchValidationResult(
                validations=[
                    QuoteValidationItem(
                        quote="5 years of robust backend engineering experience",
                        is_supported=True,
                        explanation="Candidate explicitly mentions building distributed servers for 5 years."
                    )
                ]
            ), {"prompt_tokens": 50, "completion_tokens": 20}

    result = EvidenceValidator.validate_quotes(cv, "", quotes, provider=MockJudgeProvider())
    assert result["hallucination_count"] == 0
    assert result["penalty"] == 0.0
    assert result["results"]["5 years of robust backend engineering experience"] == "PASS"
    assert "Supported by LLM judge" in result["explanations"]["5 years of robust backend engineering experience"] or "Candidate explicitly mentions" in result["explanations"]["5 years of robust backend engineering experience"]

def test_evidence_validator_llm_judge_catches_fabrication():
    """
    Tests that a completely fabricated claim is flagged as FAIL by the LLM-as-a-Judge.
    """
    cv = "Frontend engineer with 2 years of HTML, CSS, and basic JavaScript."
    quotes = ["Architected multi-region Kubernetes clusters with Istio service mesh"]
    
    class MockJudgeProvider:
        model_name = "mock-judge"
        def generate_structured(self, prompt, schema_cls, system_prompt=""):
            return BatchValidationResult(
                validations=[
                    QuoteValidationItem(
                        quote="Architected multi-region Kubernetes clusters with Istio service mesh",
                        is_supported=False,
                        explanation="CV only mentions junior frontend engineering; Kubernetes/Istio is completely absent."
                    )
                ]
            ), {"prompt_tokens": 50, "completion_tokens": 20}

    result = EvidenceValidator.validate_quotes(cv, "", quotes, provider=MockJudgeProvider())
    assert result["hallucination_count"] == 1
    assert result["penalty"] == 5.0
    assert result["results"]["Architected multi-region Kubernetes clusters with Istio service mesh"] == "FAIL"

