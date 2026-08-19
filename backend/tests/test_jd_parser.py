import pytest
from unittest.mock import MagicMock, patch
from services.jobs.schemas import ParsedJobRequirement, ParsedRequirement, RequirementType, EvaluationMode

class MockAIFactory:
    def __init__(self, expected_requirements):
        self.expected_requirements = expected_requirements
        
    def generate_structured(self, prompt, schema_cls, system_prompt):
        req = ParsedJobRequirement(
            title="Software Engineer",
            requirements=self.expected_requirements
        )
        return req, {"prompt_tokens": 10, "completion_tokens": 10}
        
    def generate_embeddings(self, text):
        return [0.1] * 1536, {"prompt_tokens": 5, "completion_tokens": 0}
        
    @property
    def model_name(self): return "mock-model"
    
    @property
    def embedding_model_name(self): return "mock-emb"

@patch('services.ai.jd_parser.get_ai_provider')
@patch('services.jobs.job_service.get_ai_provider')
def test_jd_parser_classification(mock_provider_svc, mock_provider_parser, monkeypatch):
    # Setup mock DB session
    mock_db = MagicMock()
    
    # Define our expected parsed output representing the LLM's structured extraction
    expected_reqs = [
        ParsedRequirement(
            original_text="6+ years of Python required",
            canonical_skill_name="Python",
            category="Technical",
            requirement_type=RequirementType.MANDATORY,
            minimum_experience=6,
            evaluation_mode=EvaluationMode.DETERMINISTIC
        ),
        ParsedRequirement(
            original_text="AWS is preferred",
            canonical_skill_name="AWS",
            category="Technical",
            requirement_type=RequirementType.PREFERRED,
            evaluation_mode=EvaluationMode.SEMANTIC
        )
    ]
    
    mock_ai = MockAIFactory(expected_reqs)
    mock_provider_svc.return_value = mock_ai
    mock_provider_parser.return_value = mock_ai
    
    from services.jobs.job_service import JobService
    service = JobService(mock_db)
    
    # We pass the raw text. The mock LLM intercepts it and returns our expected_reqs
    job = service.process_raw_jd("Python with 6+ years required. AWS experience is preferred.")
    
    # Assert DB Add called
    assert mock_db.add.called
    
    # Check the separated requirements on the job
    assert len(job.mandatory_skills) == 1
    assert job.mandatory_skills[0]["canonical_skill_name"] == "Python"
    
    assert len(job.preferred_skills) == 1
    assert job.preferred_skills[0]["canonical_skill_name"] == "AWS"

    # Assert embedding was attached
    assert job.embedding == [0.1] * 1536
    
    # Kubernetes is not in the text and not in the mock output, so it's not present
    assert not any("Kubernetes" in r["canonical_skill_name"] for r in job.mandatory_skills + job.preferred_skills)
