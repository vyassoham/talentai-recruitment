import io
import logging
from typing import BinaryIO, Tuple, Union

logger = logging.getLogger(__name__)

class DocumentOptimizer:
    """
    Intelligent document optimizer to drastically reduce storage footprint.
    Applies lossless compression, stream deflation, garbage collection, and 
    font/image optimization for uploaded PDF resumes.
    """

    @staticmethod
    def optimize_pdf_stream(file_obj: Union[BinaryIO, bytes], filename: str) -> Tuple[BinaryIO, int, int]:
        """
        Compresses PDF bytes using PyMuPDF lossless stream deflation and garbage cleanup.
        Returns: (optimized_file_obj, original_size, optimized_size)
        """
        extension = filename.split(".")[-1].lower() if "." in filename else ""

        if isinstance(file_obj, bytes):
            raw_bytes = file_obj
            stream_obj = io.BytesIO(raw_bytes)
        else:
            file_obj.seek(0)
            raw_bytes = file_obj.read()
            file_obj.seek(0)
            stream_obj = file_obj

        original_size = len(raw_bytes)

        if extension != "pdf" or original_size == 0:
            return stream_obj, original_size, original_size

        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=raw_bytes, filetype="pdf")

            # Apply maximum safe compression
            optimized_bytes = doc.tobytes(
                garbage=4,            # Remove unused objects and streams
                deflate=True,         # Deflate all uncompressed streams
                clean=True,           # Clean and sanitize page tree
                deflate_images=True,  # Deflate embedded images
                deflate_fonts=True    # Deflate embedded font subsets
            )
            doc.close()

            optimized_size = len(optimized_bytes)
            
            # Only use optimized version if it actually reduced or maintained size
            if optimized_size < original_size:
                saved_pct = ((original_size - optimized_size) / original_size) * 100
                logger.info(
                    f"Optimized PDF '{filename}': {original_size/1024:.1f}KB -> "
                    f"{optimized_size/1024:.1f}KB (Saved {saved_pct:.1f}% space)"
                )
                optimized_stream = io.BytesIO(optimized_bytes)
                return optimized_stream, original_size, optimized_size
            else:
                stream_obj.seek(0)
                return stream_obj, original_size, original_size

        except Exception as e:
            logger.warning(f"PDF optimization failed for '{filename}' ({e}); using original file.")
            stream_obj.seek(0)
            return stream_obj, original_size, original_size
