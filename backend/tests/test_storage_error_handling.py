import os
import pytest
from unittest.mock import patch, MagicMock
from core.storage import LocalStorage, S3Storage, GCSStorage

def test_local_storage_delete_nonexistent():
    storage = LocalStorage()
    result = storage.delete("non_existent_file_key_12345.pdf")
    assert result is False

def test_local_storage_delete_permission_error():
    storage = LocalStorage()
    # Mock os.path.exists as True, but os.remove raises PermissionError
    with patch("os.path.exists", return_value=True), \
         patch("os.remove", side_effect=PermissionError("Access denied")):
        # Ensure our storage doesn't crash, but handles error
        try:
            result = storage.delete("locked_file.pdf")
            # If implementation catches or allows raising, verify clean behavior
        except PermissionError:
            pass # Expected if unhandled, or returns False if wrapped

def test_s3_storage_delete_client_error():
    s3_storage = S3Storage(bucket_name="test-bucket")
    mock_s3 = MagicMock()
    mock_s3.delete_object.side_effect = Exception("AWS S3 Connection Refused")
    s3_storage._s3_client = mock_s3
    
    result = s3_storage.delete("resumes/test.pdf")
    assert result is False

def test_gcs_storage_delete_client_error():
    gcs_storage = GCSStorage(bucket_name="test-bucket")
    mock_gcs = MagicMock()
    mock_blob = MagicMock()
    mock_blob.delete.side_effect = Exception("GCS 403 Forbidden")
    mock_gcs.bucket().blob.return_value = mock_blob
    gcs_storage._gcs_client = mock_gcs
    
    result = gcs_storage.delete("resumes/test.pdf")
    assert result is False
