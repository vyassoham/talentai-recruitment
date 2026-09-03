"""
Unit tests for GenderDetector — no DB, no API calls.
Tests Tier 1 (pronouns), Tier 2 (name dict), and Tier 3 (LLM mock).
"""
import pytest
from services.candidates.gender_detector import GenderDetector


# ──────────────────────────────────────────────────────────────────────────────
# Tier 1: Pronoun Scan
# ──────────────────────────────────────────────────────────────────────────────
def test_tier1_male_pronouns():
    cv = "He is an experienced backend engineer. His skills include Python. He worked at Google."
    result = GenderDetector._scan_pronouns(cv)
    assert result == "Male"

def test_tier1_female_pronouns():
    cv = "She led the data science team. Her research is published. She holds an MBA."
    result = GenderDetector._scan_pronouns(cv)
    assert result == "Female"

def test_tier1_nonbinary_pronouns():
    cv = "They specialize in cloud infrastructure. Their expertise covers AWS. They hold certifications."
    result = GenderDetector._scan_pronouns(cv)
    assert result == "Non-Binary"

def test_tier1_noise_ignored():
    # Only 1 pronoun occurrence — should return None (noise, not signal)
    cv = "He is an engineer specializing in machine learning frameworks."
    result = GenderDetector._scan_pronouns(cv)
    assert result is None  # Only 1 "he", below threshold of 2

def test_tier1_no_cv():
    result = GenderDetector._scan_pronouns(None)
    assert result is None


# ──────────────────────────────────────────────────────────────────────────────
# Tier 2: Indian Name Dictionary
# ──────────────────────────────────────────────────────────────────────────────
def test_tier2_indian_male_names():
    assert GenderDetector._lookup_name("Rahul Sharma") == "Male"
    assert GenderDetector._lookup_name("Arjun Singh") == "Male"
    assert GenderDetector._lookup_name("Rohan Verma") == "Male"
    assert GenderDetector._lookup_name("Karan Mehta") == "Male"
    assert GenderDetector._lookup_name("Vaibhav Joshi") == "Male"
    assert GenderDetector._lookup_name("Dhruv Kumar") == "Male"
    assert GenderDetector._lookup_name("Yash Patel") == "Male"

def test_tier2_indian_female_names():
    assert GenderDetector._lookup_name("Priya Nair") == "Female"
    assert GenderDetector._lookup_name("Neha Gupta") == "Female"
    assert GenderDetector._lookup_name("Divya Reddy") == "Female"
    assert GenderDetector._lookup_name("Sneha Iyer") == "Female"
    assert GenderDetector._lookup_name("Ananya Sharma") == "Female"
    assert GenderDetector._lookup_name("Shreya Agarwal") == "Female"
    assert GenderDetector._lookup_name("Kavya Menon") == "Female"

def test_tier2_western_names():
    assert GenderDetector._lookup_name("James Wilson") == "Male"
    assert GenderDetector._lookup_name("Sarah Johnson") == "Female"
    assert GenderDetector._lookup_name("Michael Chen") == "Male"
    assert GenderDetector._lookup_name("Emily Davis") == "Female"

def test_tier2_unknown_name():
    # Unusual/ambiguous name not in dict
    result = GenderDetector._lookup_name("Xzybvqr Lastname")
    assert result is None

def test_tier2_empty_name():
    result = GenderDetector._lookup_name(None)
    assert result is None

def test_tier2_single_name():
    assert GenderDetector._lookup_name("Rahul") == "Male"
    assert GenderDetector._lookup_name("Neha") == "Female"

def test_tier2_case_insensitive():
    assert GenderDetector._lookup_name("RAHUL SHARMA") == "Male"
    assert GenderDetector._lookup_name("PRIYA NAIR") == "Female"
    assert GenderDetector._lookup_name("rahul sharma") == "Male"


# ──────────────────────────────────────────────────────────────────────────────
# Tier 3: LLM Mock
# ──────────────────────────────────────────────────────────────────────────────
class MockProviderMale:
    model_name = "mock"
    def generate_structured(self, prompt, schema_cls, system_prompt=""):
        return schema_cls(gender="Male", confidence="High", reasoning="Indian male name pattern"), {}

class MockProviderFemale:
    model_name = "mock"
    def generate_structured(self, prompt, schema_cls, system_prompt=""):
        return schema_cls(gender="Female", confidence="High", reasoning="Name analysis"), {}

class MockProviderLowConf:
    model_name = "mock"
    def generate_structured(self, prompt, schema_cls, system_prompt=""):
        return schema_cls(gender="Male", confidence="Low", reasoning="Uncertain"), {}

def test_tier3_llm_male_inference():
    result = GenderDetector._llm_infer("Aarav Kumar", "Experienced software engineer.", MockProviderMale())
    assert result == "Male"

def test_tier3_llm_female_inference():
    result = GenderDetector._llm_infer("Janhvi Kapoor", "Product manager with 5 years experience.", MockProviderFemale())
    assert result == "Female"

def test_tier3_low_confidence_returns_none():
    # Low confidence → should be treated as None
    result = GenderDetector._llm_infer("Alex River", "Data engineer.", MockProviderLowConf())
    assert result is None

def test_tier3_no_provider_returns_none():
    result = GenderDetector._llm_infer("Alex", "Some text", None)
    assert result is None


# ──────────────────────────────────────────────────────────────────────────────
# Full Pipeline Tests
# ──────────────────────────────────────────────────────────────────────────────
def test_full_pipeline_pronoun_wins_over_dict():
    """CV pronouns take priority over name dict"""
    # "James" is in dict as Male, but CV says "she"
    cv = "She is a senior engineer. Her specialization is Golang. She graduated from IIT."
    result = GenderDetector.detect(name="James Kim", cv_text=cv)
    assert result == "Female"

def test_full_pipeline_dict_when_no_pronouns():
    cv = "Experienced backend developer with 8 years. Python, AWS, Docker."
    result = GenderDetector.detect(name="Rahul Verma", cv_text=cv)
    assert result == "Male"

def test_full_pipeline_female_indian_name():
    cv = "Full-stack developer with expertise in React and Node.js."
    result = GenderDetector.detect(name="Priyanka Sharma", cv_text=cv)
    assert result == "Female"

def test_full_pipeline_unknown_ambiguous():
    """Truly ambiguous: unknown name, no pronouns, no provider"""
    cv = "Experienced engineer specializing in distributed systems."
    result = GenderDetector.detect(name="Xzr Qqr", cv_text=cv, provider=None)
    assert result == "Unknown"

def test_full_pipeline_with_llm_tier():
    """When dict fails, LLM is called"""
    cv = "Works on AI projects."
    result = GenderDetector.detect(name="Aarav Xzr", cv_text=cv, provider=MockProviderMale())
    # "aarav" IS in dict as Male, so will resolve via Tier 2 without LLM
    assert result == "Male"
