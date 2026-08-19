import io
import pytest
from core.storage import LocalStorage, S3Storage, GCSStorage, get_storage_provider
from core.security import SecurityUtils
from core.config import settings

def test_local_storage_crud():
    storage = LocalStorage()
    content = b"Candidate Resume Test Content"
    file_obj = io.BytesIO(content)
    
    key = storage.save(file_obj, "resume.pdf")
    assert key.endswith(".pdf")
    
    path = storage.get(key)
    assert path is not None
    
    deleted = storage.delete(key)
    assert deleted is True

def test_storage_factory_fallback():
    provider = get_storage_provider()
    assert provider is not None
    assert isinstance(provider, (LocalStorage, S3Storage, GCSStorage))

def test_clamav_scanner_clean_file():
    content = b"Clean PDF Content"
    is_clean, threat = SecurityUtils.scan_file_for_malware(content)
    assert is_clean is True
    assert threat is None
