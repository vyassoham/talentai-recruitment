import re
import string

class EvidenceValidator:
    """
    Independently verifies that the evidence quotes provided by the AI 
    actually exist in the source document (CV text).
    """
    
    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Removes punctuation, extra whitespace, and lowercases text
        to allow for robust substring matching.
        """
        if not text:
            return ""
        # Lowercase
        text = text.lower()
        # Remove punctuation
        text = text.translate(str.maketrans('', '', string.punctuation))
        # Normalize whitespace (replace multiple spaces/newlines with single space)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @classmethod
    def validate_quotes(cls, source_text: str, external_evidence: str, quotes: list[str]) -> dict:
        """
        Validates a list of quotes against the combined source text.
        Returns a dictionary with validation results and a calculated penalty.
        """
        normalized_source = cls._normalize_text(source_text)
        if external_evidence:
            normalized_source += " " + cls._normalize_text(external_evidence)
            
        validation_results = {}
        hallucination_count = 0
        
        for quote in quotes:
            if not quote or quote.lower() in ["none", "n/a", "not mentioned"]:
                validation_results[quote] = "PASS" # Not a real quote, just an absence of evidence
                continue
                
            norm_quote = cls._normalize_text(quote)
            
            # If the normalized quote is found within the normalized source, it's valid
            if norm_quote and norm_quote in normalized_source:
                validation_results[quote] = "PASS"
            else:
                # Fallback: check if 70% of the words in the quote appear anywhere in the source
                # This handles minor LLM paraphrasing errors while still catching pure hallucinations
                words = norm_quote.split()
                if len(words) > 3:
                    quote_vocab = set(words)
                    source_vocab = set(normalized_source.split())
                    match_ratio = len(quote_vocab.intersection(source_vocab)) / len(quote_vocab)
                    if match_ratio >= 0.7:
                        validation_results[quote] = "PASS"
                        continue
                        
                validation_results[quote] = "FAIL"
                hallucination_count += 1
                
        # Calculate score penalty (e.g., -5 points per hallucinated quote)
        penalty = hallucination_count * 5.0
        
        return {
            "results": validation_results,
            "hallucination_count": hallucination_count,
            "penalty": penalty
        }
