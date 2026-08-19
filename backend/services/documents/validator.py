import os
import logging
from typing import BinaryIO, Tuple
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
    ALLOWED_MIME_TYPES = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    MAX_FILE_SIZE_MB = settings.MAX_CV_FILE_SIZE_MB
    MAX_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

    @classmethod
    def validate(cls, file_obj: BinaryIO, filename: str) -> Tuple[bool, str]:
        """
        Validates file size, extension, magic byte MIME type, and scans for malware via ClamAV.
        Returns: (is_valid, error_message)
        """
        # 1. Check File Size
        file_obj.seek(0, os.SEEK_END)
        size = file_obj.tell()
        file_obj.seek(0)

        if size > cls.MAX_BYTES:
            return False, f"File size exceeds maximum allowed ({cls.MAX_FILE_SIZE_MB}MB)"
            
        if size == 0:
            return False, "File is empty (0 bytes)"

        # 2. Check File Extension
        ext = os.path.splitext(filename)[1].lower()
        if ext not in cls.ALLOWED_EXTENSIONS:
            return False, f"Unsupported file extension: {ext}"

        # 3. Read content for MIME detection & Malware inspection
        content = file_obj.read()
        file_obj.seek(0)
        
        # 4. ClamAV Antivirus Scanning
        is_clean, threat = SecurityUtils.scan_file_for_malware(content)
        if not is_clean:
            return False, f"Security Violation: Malware detected ({threat})"

        # 5. MIME Type Detection
        try:
            if HAS_MAGIC:
                chunk = content[:2048]
                mime = magic.from_buffer(chunk, mime=True)
                if mime not in cls.ALLOWED_MIME_TYPES:
                    if ext == '.docx' and mime == 'application/zip':
                        pass # Allow docx zip containers
                    else:
                        return False, f"Unsupported MIME type: {mime}"
        except Exception as e:
            logger.debug(f"MIME magic check skipped: {e}")

        return True, ""
