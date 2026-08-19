import pytest
from services.ai.validator import EvidenceValidator

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
    
    result = EvidenceValidator.validate_quotes(cv, "", quotes)
    assert result["hallucination_count"] == 1
    assert result["penalty"] == 15.0
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
    
    result = EvidenceValidator.validate_quotes(cv, "", quotes)
    assert result["hallucination_count"] == 0 # Should pass because 80% matches
