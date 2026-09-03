import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from services.candidates.experience import ExperienceCalculator
from services.documents.schemas import ParsedEmployment
from services.documents.validator import DocumentValidator
import tempfile

def test_experience_calculator():
    employments = [
        ParsedEmployment(company="A", title="Dev", start_date="2020-01-01", end_date="2021-01-01", description="", skills=[]),
        ParsedEmployment(company="B", title="Dev", start_date="2020-06-01", end_date="2022-01-01", description="", skills=[])
    ]
    # Dates: Jan 2020 to Jan 2021 AND Jun 2020 to Jan 2022
    # Merged: Jan 2020 to Jan 2022 -> exactly 2 years
    exp = ExperienceCalculator.calculate_total_experience(employments)
    assert 1.9 < exp < 2.1 # Approx 2 years depending on leap years

def test_document_validator():
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        # Test empty file
        is_valid, err = DocumentValidator.validate(tmp, "empty.pdf")
        assert not is_valid
        assert "empty" in err
        
        # Note: magic mime detection might fail locally without libmagic, 
        # so we won't assert the True path strictly in this mock test without real files.
