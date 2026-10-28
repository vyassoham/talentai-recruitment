import os
import io
import re
import logging
from typing import BinaryIO, Tuple, Union, Optional
from collections import Counter
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

    INVALID_NAME_PLACEHOLDERS = {
        "resume", "cv", "curriculum vitae", "curriculum_vitae", "curriculum-vitae",
        "candidate", "candidate name", "candidatename", "applicant", "applicant name",
        "unknown", "unknown candidate", "unnamed", "anonymous", "n/a", "na",
        "none", "null", "nil", "undefined", "profile", "user profile",
        "candidate profile", "biodata", "bio data", "bio-data", "document",
        "document title", "untitled", "sample resume", "template", "placeholder",
        "first last", "firstname lastname", "name", "your name", "enter name",
        "full name", "personal details", "contact details", "summary",
        "experience", "education", "skills", "declaration", "page 1", "page 1 of 1",
    }

    @classmethod
    def validate(cls, file_obj: Union[BinaryIO, bytes], filename: str) -> Tuple[bool, str]:
        """
        Strict enterprise validation for uploaded candidate CV documents.
        Enforces:
        1. Non-empty filename & path traversal neutralization
        2. Strict extension whitelist (.pdf, .docx, .doc, .txt)
        3. Strict file size bounds (min 32 bytes, max configured MB)
        4. Dangerous binary and script magic header rejection (ELF, PE/EXE, scripts)
        5. Genuine magic byte matching for claimed extension (PDF %PDF-, DOCX PKzip)
        6. ClamAV daemon antivirus stream scanning
        """
        if not filename or not str(filename).strip():
            return False, "Security Violation: Filename cannot be empty or missing."

        # Path traversal neutralization
        safe_filename = os.path.basename(str(filename).replace("\\", "/"))
        ext = os.path.splitext(safe_filename)[1].lower()

        if ext not in cls.ALLOWED_EXTENSIONS:
            return False, f"Security Violation: File extension '{ext}' is not permitted. Only {', '.join(cls.ALLOWED_EXTENSIONS)} files are allowed."

        if isinstance(file_obj, bytes):
            content = file_obj
            size = len(content)
        else:
            file_obj.seek(0, os.SEEK_END)
            size = file_obj.tell()
            file_obj.seek(0)
            content = file_obj.read()
            file_obj.seek(0)

        # 1. Check File Size Bounds
        if size > cls.MAX_BYTES:
            return False, f"File size exceeds maximum allowed ({cls.MAX_FILE_SIZE_MB}MB)"
            
        if size < 32:
            return False, "File is too small or empty (minimum 32 bytes required for valid document headers)"

        # 2. Block Dangerous Executable / Script Magic Headers
        dangerous_headers = [
            (b"MZ", "Windows Executable / Dynamic Link Library (.exe, .dll)"),
            (b"\x7fELF", "Linux Executable Binary (ELF)"),
            (b"#!/", "Unix Shell Script"),
            (b"<?php", "PHP Script"),
            (b"<script", "HTML/JavaScript Payload"),
            (b"\xca\xfe\xba\xbe", "Java Bytecode Class File"),
            (b"\x50\x4b\x05\x06", "Corrupted or Empty Zip Container"),
        ]
        for magic_prefix, desc in dangerous_headers:
            if content.startswith(magic_prefix) or (magic_prefix == b"<script" and b"<script" in content[:256].lower()):
                return False, f"Security Violation: Uploaded file contains forbidden executable/script content ({desc})"

        # 3. Magic Byte Verification for Claimed Extension
        if ext == ".pdf":
            if not content.startswith(b"%PDF-"):
                return False, "Security Violation: File extension is .pdf but content does not start with valid PDF magic bytes (%PDF-)."
        elif ext == ".docx":
            if not content.startswith(b"PK\x03\x04"):
                return False, "Security Violation: File extension is .docx but content does not match valid OpenXML PKzip container."
        elif ext == ".doc":
            if not content.startswith(b"\xd0\xcf\x11\xe0"):
                return False, "Security Violation: File extension is .doc but content does not match valid OLE document container."
        elif ext == ".txt":
            try:
                content[:1024].decode("utf-8")
            except UnicodeDecodeError:
                return False, "Security Violation: Plain text file contains invalid non-UTF8 binary data."

        # 4. ClamAV Antivirus Scanning
        is_clean, threat = SecurityUtils.scan_file_for_malware(content)
        if not is_clean:
            return False, f"Security Violation: Malware detected ({threat})"

        return True, ""

    @classmethod
    def validate_candidate_name(cls, name: Optional[str]) -> Tuple[bool, str]:
        """
        Validates whether an extracted candidate name is genuine, non-empty, and not a placeholder/junk.
        Returns: (is_valid, error_message)
        """
        if not name or not str(name).strip():
            return False, "Candidate name cannot be empty or null"
        
        cleaned = str(name).strip()
        
        # Check normalized placeholder tokens
        norm = re.sub(r'[\s_\-]+', ' ', cleaned.lower()).strip()
        if norm in cls.INVALID_NAME_PLACEHOLDERS:
            return False, f"Name '{cleaned}' is a generic placeholder or document header, not a candidate name"
            
        # Check if name is actually a filename (e.g. "resume_john.pdf")
        if any(cleaned.lower().endswith(ext) for ext in ['.pdf', '.docx', '.doc', '.txt', '.rtf']):
            return False, f"Name '{cleaned}' appears to be a filename rather than a person's name"
            
        # Check length bounds
        if len(cleaned) < 2:
            return False, f"Candidate name '{cleaned}' is too short (min 2 characters)"
        if len(cleaned) > 90:
            return False, f"Candidate name is too long ({len(cleaned)} chars, max 90 chars)"

        # Check for web URLs or emails
        if "@" in cleaned or ".com" in cleaned.lower() or "http" in cleaned.lower() or "www." in cleaned.lower():
            return False, f"Candidate name '{cleaned}' contains an email address or URL"

        # Check for minimum alphabetic characters (e.g. prevent "12345" or "---")
        alpha_chars = [c for c in cleaned if c.isalpha()]
        if len(alpha_chars) < 2:
            return False, f"Candidate name '{cleaned}' must contain at least 2 alphabetic characters"

        # Check for multiline or paragraph text extracted as name
        if "\n" in cleaned or "\r" in cleaned:
            return False, "Candidate name contains invalid newline characters"

        return True, ""

    @classmethod
    def clean_candidate_name(cls, name: Optional[str]) -> Optional[str]:
        """
        Cleans and standardizes a validated candidate name.
        """
        if not name:
            return None
            
        cleaned = str(name).strip()
        # Remove surrounding quotes, backticks, or markdown formatting
        cleaned = cleaned.strip("\"'`*#_ ")
        # Collapse multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        # Remove trailing commas, colons, hyphens
        cleaned = cleaned.rstrip(",;:- ")
        
        # If name is fully uppercase (e.g. "RAHUL SHARMA") or all lowercase, convert to title case
        if (cleaned.isupper() or cleaned.islower()) and len(cleaned) > 2:
            cleaned = cleaned.title()
            
        return cleaned

    @classmethod
    def validate_extracted_text(cls, text: Optional[str]) -> Tuple[bool, str]:
        """
        Validates raw or normalized extracted CV text before sending to LLM.
        Guards against empty files, whitespace-only, OCR failures, binary dumps, and character loops.
        Returns: (is_valid, error_message)
        """
        if not text or not str(text).strip():
            return False, "Document text is empty or contains only whitespace"
            
        stripped = str(text).strip()

        # 1. Unicode replacement character check (\ufffd) - indicate failed/corrupted OCR decode
        replacement_count = stripped.count('\ufffd')
        if replacement_count > 5 and (replacement_count / len(stripped)) > 0.03:
            return False, "Document text contains excessive corrupted Unicode replacement glyphs (failed OCR)"

        # 2. Printable character ratio (reject binary files or corrupted encoding)
        printable_count = sum(1 for c in stripped if c.isprintable() or c in '\n\r\t')
        printable_ratio = printable_count / len(stripped)
        if printable_ratio < 0.85:
            return False, f"Document contains excessive unreadable binary or non-printable characters (printable ratio {printable_ratio:.1%})"

        # 3. Minimum character length check (a real CV has at least contact info + 1 job/education)
        if len(stripped) < 80:
            return False, f"Document text too short ({len(stripped)} chars, min 80) to be a valid Resume/CV"
            
        # 4. Minimum word count check
        words = stripped.split()
        if len(words) < 15:
            return False, f"Document text has insufficient word count ({len(words)} words, min 15)"

        # 5. Alphabetic character ratio (reject sheets of pure numbers, symbols, or un-OCRed noise)
        alpha_count = sum(1 for c in stripped if c.isalpha())
        alpha_ratio = alpha_count / len(stripped)
        if alpha_ratio < 0.30:
            return False, f"Document text lacks sufficient alphabetic text (alpha ratio {alpha_ratio:.1%}, min 30% required)"

        # 6. Repetitive character spam (e.g. looping OCR bug like "aaaaaaaaaaaa...")
        non_ws = [c for c in stripped if not c.isspace()]
        if non_ws:
            most_common, count = Counter(non_ws).most_common(1)[0]
            if count / len(non_ws) > 0.50:
                return False, f"Document text consists primarily of repetitive character spam ('{most_common}')"

        return True, ""

