import pytest
from pydantic import ValidationError
from services.documents.validator import DocumentValidator
from services.documents.schemas import StructuredCandidate, ParsedSkill, ParsedEmployment

def test_validate_candidate_name_valid():
    valid_names = [
        "John Doe",
        "Rahul Sharma",
        "Sarah O'Connor",
        "Jean-Luc Picard",
        "Dr. Alice Bob, Ph.D.",
        "Md. Al-Amin",
        "Priya Patel",
    ]
    for name in valid_names:
        is_valid, err = DocumentValidator.validate_candidate_name(name)
        assert is_valid, f"Expected '{name}' to be valid, but got: {err}"

def test_clean_candidate_name():
    assert DocumentValidator.clean_candidate_name("  JOHN DOE  ") == "John Doe"
    assert DocumentValidator.clean_candidate_name('"Alice Smith"') == "Alice Smith"
    assert DocumentValidator.clean_candidate_name("**Rahul Sharma**") == "Rahul Sharma"
    assert DocumentValidator.clean_candidate_name("Bob   Builder ,") == "Bob Builder"

def test_validate_candidate_name_rejects_placeholders():
    placeholders = [
        "Resume",
        "RESUME",
        "Curriculum Vitae",
        "cv",
        "Candidate",
        "Applicant",
        "Unknown",
        "unknown candidate",
        "N/A",
        "None",
        "null",
        "Profile",
        "Bio Data",
        "Document",
        "Untitled",
    ]
    for p in placeholders:
        is_valid, err = DocumentValidator.validate_candidate_name(p)
        assert not is_valid, f"Expected placeholder '{p}' to be rejected"
        assert "placeholder" in err.lower() or "generic" in err.lower()

def test_validate_candidate_name_rejects_junk_and_filenames():
    junk_names = [
        "",
        "   ",
        None,
        "resume.pdf",
        "my_cv_2026.docx",
        "12345",
        "---",
        "A",
        "john.doe@example.com",
        "https://linkedin.com/in/alice",
        "This is a very long paragraph extracted as a candidate name that definitely exceeds standard length limits because of poor OCR.",
    ]
    for j in junk_names:
        is_valid, err = DocumentValidator.validate_candidate_name(j)
        assert not is_valid, f"Expected junk name '{j}' to be rejected"

def test_validate_extracted_text_valid():
    valid_text = """
    Rahul Sharma
    Senior Full-Stack Software Engineer
    Email: rahul.sharma@example.com | Phone: +91 9876543210 | Bengaluru, India
    
    Professional Summary:
    Results-driven Software Engineer with 6+ years of experience designing scalable microservices in Python, FastAPI, and PostgreSQL.
    
    Work Experience:
    Senior Developer | TechCorp India (2021 - Present)
    - Architected distributed background processing queue using Redis and Celery.
    - Improved search query latency by 45% using PostgreSQL vector embeddings and indexing.
    
    Education & Skills:
    B.Tech Computer Science | IIT Bombay (2015 - 2019)
    Skills: Python, TypeScript, React, Docker, Kubernetes, AWS, PostgreSQL.
    """
    is_valid, err = DocumentValidator.validate_extracted_text(valid_text)
    assert is_valid, f"Expected valid resume text to pass, got: {err}"

def test_validate_extracted_text_rejects_empty_and_short():
    assert DocumentValidator.validate_extracted_text("")[0] is False
    assert DocumentValidator.validate_extracted_text("   \n\t  ")[0] is False
    assert DocumentValidator.validate_extracted_text("Short text with only five words here.")[0] is False

def test_validate_extracted_text_rejects_binary_and_unreadable_ocr():
    # Corrupted unicode replacement character flood
    corrupted = "\ufffd" * 50 + " Rahul Sharma Python Developer " + "\ufffd" * 50
    is_valid, err = DocumentValidator.validate_extracted_text(corrupted)
    assert not is_valid
    assert "unicode" in err.lower() or "ocr" in err.lower()

    # Repetitive looping OCR character spam
    spam = "a" * 300 + " " + "developer engineer python backend software engineer fullstack cloud " * 3
    is_valid, err = DocumentValidator.validate_extracted_text(spam)
    assert not is_valid
    assert "repetitive" in err.lower()

    # Non-alphabetic noise (numbers and symbols only)
    symbols = "123456789 0987654321 !@#$%^&*()_+ ==================" * 5
    is_valid, err = DocumentValidator.validate_extracted_text(symbols)
    assert not is_valid
    assert "alphabetic" in err.lower()

def test_structured_candidate_name_validation_integration():
    # Valid resume with valid name
    cand = StructuredCandidate(
        is_valid_resume=True,
        name="  alice smith  ",
        skills=[ParsedSkill(original_name="Python", years_of_experience=3.0)],
        employment_history=[ParsedEmployment(company="Acme Corp", title="Software Engineer")]
    )
    assert cand.is_valid_resume is True
    assert cand.name == "Alice Smith"

    # LLM says is_valid_resume=True, but name is placeholder "Resume" -> Must automatically flip to False
    cand_placeholder = StructuredCandidate(
        is_valid_resume=True,
        name="Resume",
        skills=[ParsedSkill(original_name="Python")]
    )
    assert cand_placeholder.is_valid_resume is False
    assert "Invalid candidate name" in cand_placeholder.validation_reason

    # LLM says is_valid_resume=True, but name is None
    cand_no_name = StructuredCandidate(
        is_valid_resume=True,
        name=None,
        skills=[ParsedSkill(original_name="Python")]
    )
    assert cand_no_name.is_valid_resume is False
    assert "Invalid candidate name" in cand_no_name.validation_reason

    # Completely blank candidate (no skills, no employment, no contact)
    cand_blank = StructuredCandidate(
        is_valid_resume=True,
        name="Valid Person",
        skills=[],
        employment_history=[]
    )
    assert cand_blank.is_valid_resume is False
    assert "no extractable skills" in cand_blank.validation_reason.lower()

def test_candidate_service_name_guard():
    from unittest.mock import MagicMock
    from services.candidates.candidate_service import CandidateService

    mock_db = MagicMock()
    service = CandidateService(mock_db)

    # Attempting to save candidate with invalid name raises ValueError
    bad_candidate_data = MagicMock()
    bad_candidate_data.name = "Unknown"
    
    mock_doc = MagicMock()
    mock_db.get.return_value = mock_doc

    with pytest.raises(ValueError, match="Cannot save candidate without a valid name"):
        service.save_structured_candidate(document_id=1, structured_data=bad_candidate_data)

def test_ingestion_pipeline_rejects_junk_text_without_calling_llm():
    from unittest.mock import MagicMock, patch
    from services.jobs.ingestion_jobs import IngestionPipeline

    mock_job = MagicMock()
    mock_job.stage = "EXTRACTING"
    mock_job.status = "IN_PROGRESS"

    mock_doc = MagicMock()
    mock_doc.storage_key = "cvs/junk.txt"
    mock_doc.raw_extracted_text = "   \n\t  "

    mock_db = MagicMock()
    mock_db.get.side_effect = lambda model, obj_id: mock_job if "IngestionJob" in str(model) else mock_doc

    pipeline = IngestionPipeline("job-junk-123")

    with patch("services.jobs.ingestion_jobs.SessionLocal", return_value=mock_db), \
         patch("services.documents.extractor.DocumentExtractor.extract_text", return_value="   "), \
         patch("services.ai.cv_parser.CVParser.parse_cv") as mock_parse_cv:
        
        result = pipeline.run()
        
        # Pipeline must fail cleanly
        assert result["status"] == "FAILED"
        assert "Invalid CV content" in result["error"]
        
        # LLM MUST NOT have been called!
        mock_parse_cv.assert_not_called()

def test_ingestion_pipeline_handles_invalid_resume_without_delete_crash():
    from unittest.mock import MagicMock, patch
    from services.jobs.ingestion_jobs import IngestionPipeline

    mock_job = MagicMock()
    mock_job.stage = "PARSING"
    mock_job.status = "IN_PROGRESS"

    mock_doc = MagicMock()
    mock_doc.normalized_text = "Valid length text that will be parsed by parser but is not a resume." * 5

    mock_db = MagicMock()
    mock_db.get.side_effect = lambda model, obj_id: mock_job if "IngestionJob" in str(model) else mock_doc

    mock_structured = MagicMock()
    mock_structured.is_valid_resume = False
    mock_structured.validation_reason = "Document is a restaurant menu, not a CV"

    pipeline = IngestionPipeline("job-menu-456")

    with patch("services.jobs.ingestion_jobs.SessionLocal", return_value=mock_db), \
         patch("services.ai.cv_parser.CVParser.parse_cv", return_value=mock_structured):
        
        result = pipeline.run()
        
        assert result["status"] == "FAILED"
        assert result["error"] == "Document is a restaurant menu, not a CV"
        # Verify db.delete(doc) was NOT called (which causes Foreign Key Violations)
        mock_db.delete.assert_not_called()

