import os
import io
import logging
from typing import BinaryIO, Tuple, Union
from core.config import settings
from core.security import SecurityUtils

logger = logging.getLogger(__name__)

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

class DocumentValidationError(Exception):
    pass

class DocumentValidator:
    ALLOWED_EXTENSIONS = [ext.strip().lower() for ext in settings.ALLOWED_CV_EXTENSIONS]
    ALLOWED_MIME_TYPES = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword", "text/plain"]
    MAX_FILE_SIZE_MB = settings.MAX_CV_FILE_SIZE_MB
    MAX_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

    @classmethod
    def validate(cls, file_obj: Union[BinaryIO, bytes], filename: str) -> Tuple[bool, str]:
        """
        Validates file size, extension, magic byte MIME type, and scans for malware via ClamAV.
        Returns: (is_valid, error_message)
        """
        if isinstance(file_obj, bytes):
            content = file_obj
            size = len(content)
        else:
            file_obj.seek(0, os.SEEK_END)
            size = file_obj.tell()
            file_obj.seek(0)
            content = file_obj.read()
            file_obj.seek(0)

        # 1. Check File Size
        if size > cls.MAX_BYTES:
            return False, f"File size exceeds maximum allowed ({cls.MAX_FILE_SIZE_MB}MB)"
            
        if size == 0:
            return False, "File is empty (0 bytes)"

        # 3. ClamAV Antivirus Scanning
        is_clean, threat = SecurityUtils.scan_file_for_malware(content)
        if not is_clean:
            return False, f"Security Violation: Malware detected ({threat})"

        return True, ""
