import re

class TextNormalizer:
    @staticmethod
    def normalize(text: str) -> str:
        """
        Cleans up raw extracted text for AI parsing.
        """
        if not text:
            return ""
            
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Replace multiple spaces with a single space
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Replace multiple newlines with double newline
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Strip trailing/leading whitespace
        text = text.strip()
        
        # Ensure standard unicode (NFKC)
        import unicodedata
        text = unicodedata.normalize('NFKC', text)
        
        return text
