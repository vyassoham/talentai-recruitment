import os
from typing import Optional
from core.storage import StorageInterface, get_storage_provider

class ExtractionError(Exception):
    pass

class DocumentExtractor:
    def __init__(self, storage: Optional[StorageInterface] = None):
        if storage is None:
            storage = get_storage_provider()
        self.storage = storage

    def extract_text(self, storage_key: str) -> str:
        """
        Extracts raw text from the stored document.
        Supports PDF and DOCX.
        """
        file_path = self.storage.get(storage_key)
        temp_downloaded_path = None
        
        # If storage.get returns a remote URL (e.g. Supabase, S3, GCS), fetch it to a temporary file
        if file_path.startswith("http://") or file_path.startswith("https://"):
            import tempfile
            import requests
            try:
                resp = requests.get(file_path, timeout=30)
                resp.raise_for_status()
                ext = os.path.splitext(storage_key)[1].lower()
                tmp_f = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                tmp_f.write(resp.content)
                tmp_f.close()
                file_path = tmp_f.name
                temp_downloaded_path = file_path
            except Exception as e:
                raise ExtractionError(f"Failed to fetch remote document from {file_path}: {e}")

        if not os.path.exists(file_path):
            raise ExtractionError(f"File not found: {storage_key}")

        ext = os.path.splitext(storage_key)[1].lower()
        
        try:
            if ext == '.pdf':
                raw_text = self._extract_pdf(file_path)
            elif ext == '.docx':
                raw_text = self._extract_docx(file_path)
            elif ext in ['.txt', '.md', '.csv']:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    raw_text = f.read()
            else:
                raise ExtractionError(f"Unsupported extraction format: {ext}")

            if not raw_text or not raw_text.strip():
                raise ExtractionError(f"Extracted document content is empty or whitespace-only ({ext})")

            return raw_text
        except Exception as e:
            if isinstance(e, ExtractionError):
                raise
            raise ExtractionError(f"Failed to extract text: {str(e)}")
        finally:
            if temp_downloaded_path and os.path.exists(temp_downloaded_path):
                try:
                    os.remove(temp_downloaded_path)
                except Exception:
                    pass

    def _extract_pdf(self, file_path: str) -> str:
        text_parts = []
        # Attempt 1: Try PyMuPDF (fitz)
        try:
            import fitz
            with fitz.open(file_path) as doc:
                for page in doc:
                    text_parts.append(page.get_text())
            combined = "\n\n".join(text_parts).strip()
            if combined:
                return combined
        except Exception:
            text_parts = []

        # Attempt 2: Fallback to pypdf (pure Python, reliable in all Windows environments)
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text_parts.append(extracted)
            combined = "\n\n".join(text_parts).strip()
            if not combined:
                raise ExtractionError("PDF appears to be empty or scanned without readable OCR text.")
            return combined
        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(f"PDF Extraction Error: {e}")

    def _extract_docx(self, file_path: str) -> str:
        import docx
        text_parts = []
        try:
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                text_parts.append(para.text)
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        text_parts.append(cell.text)
            combined = "\n".join(text_parts).strip()
            if not combined:
                raise ExtractionError("DOCX appears to be empty or contains no readable text.")
            return combined
        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(f"python-docx Error: {e}")
