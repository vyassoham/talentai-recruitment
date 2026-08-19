import os
import json
import time
import requests
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Type, TypeVar
from pydantic import BaseModel
from core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

class AIProviderError(Exception):
    def __init__(self, message: str, retryable: bool):
        super().__init__(message)
        self.retryable = retryable

class AIProvider(ABC):
    @abstractmethod
    def generate_structured(self, prompt: str, schema_cls: Type[T], system_prompt: str = "") -> tuple[T, dict]:
        """
        Returns (Parsed_Pydantic_Object, usage_metrics_dict)
        usage_metrics_dict should contain {'prompt_tokens': int, 'completion_tokens': int}
        """
        pass

    @abstractmethod
    def generate_embeddings(self, text: str) -> tuple[List[float], dict]:
        """
        Returns (Embedding_Vector, usage_metrics_dict)
        """
        pass
        
    @property
    @abstractmethod
    def model_name(self) -> str:
        pass
        
    @property
    @abstractmethod
    def embedding_model_name(self) -> str:
        pass

class MockProvider(AIProvider):
    def generate_structured(self, prompt: str, schema_cls: Type[T], system_prompt: str = "") -> tuple[T, dict]:
        try:
            instance = schema_cls.model_construct()
            return instance, {"prompt_tokens": 10, "completion_tokens": 10}
        except Exception:
            return None, {"prompt_tokens": 0, "completion_tokens": 0}

    def generate_embeddings(self, text: str) -> tuple[List[float], dict]:
        import random
        return [random.uniform(-1, 1) for _ in range(1536)], {"prompt_tokens": 5, "completion_tokens": 0}
        
    @property
    def model_name(self) -> str:
        return "mock-model"
        
    @property
    def embedding_model_name(self) -> str:
        return "mock-embedding"

class GeminiProvider(AIProvider):
    """
    Native Google Gemini LLM & Embedding provider using Google AI Studio.
    Supports free tier inference with Gemini 3.6/2.5/1.5 Flash and 1536-d vector embeddings.
    """
    def __init__(self, api_key: str, model: str = None, embedding_model: str = None):
        self.api_key = api_key
        self._model = model or settings.GEMINI_MODEL
        self._embedding_model = embedding_model or settings.GEMINI_EMBEDDING_MODEL
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def embedding_model_name(self) -> str:
        return self._embedding_model

    def generate_structured(self, prompt: str, schema_cls: Type[T], system_prompt: str = "") -> tuple[T, dict]:
        schema_json = schema_cls.model_json_schema()
        full_system_instruction = (
            f"{system_prompt}\n\n"
            f"You MUST output strictly valid JSON conforming to this JSON Schema:\n"
            f"{json.dumps(schema_json)}\n"
            f"Do not wrap output in markdown fences (no ```json or ```). Output raw JSON only."
        )

        url = f"{self.base_url}/models/{self._model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"System Context:\n{full_system_instruction}\n\nUser Request:\n{prompt}"}]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1
            }
        }

        try:
            resp = requests.post(url, json=payload, timeout=45)
            if resp.status_code == 429:
                raise AIProviderError("Gemini API Rate Limit Exceeded", retryable=True)
            elif resp.status_code >= 500:
                raise AIProviderError(f"Gemini Server Error: {resp.status_code}", retryable=True)
            elif resp.status_code != 200:
                raise AIProviderError(f"Gemini API Error ({resp.status_code}): {resp.text}", retryable=False)

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates or not candidates[0].get("content", {}).get("parts"):
                raise AIProviderError("No response candidates returned by Gemini", retryable=True)

            raw_text = candidates[0]["content"]["parts"][0]["text"].strip()
            
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

            instance = schema_cls.model_validate_json(raw_text)

            usage_meta = data.get("usageMetadata", {})
            usage = {
                "prompt_tokens": usage_meta.get("promptTokenCount", len(prompt) // 4),
                "completion_tokens": usage_meta.get("candidatesTokenCount", len(raw_text) // 4)
            }
            return instance, usage

        except AIProviderError:
            raise
        except Exception as e:
            logger.error(f"Gemini structured generation failed: {e}", exc_info=True)
            raise AIProviderError(f"Gemini generation error: {e}", retryable=False)

    def generate_embeddings(self, text: str) -> tuple[List[float], dict]:
        url = f"{self.base_url}/models/{self._embedding_model}:embedContent?key={self.api_key}"
        payload = {
            "model": f"models/{self._embedding_model}",
            "content": {"parts": [{"text": text}]},
            "outputDimensionality": 1536
        }

        try:
            resp = requests.post(url, json=payload, timeout=30)
            if resp.status_code == 429:
                raise AIProviderError("Gemini Embedding Rate Limit", retryable=True)
            elif resp.status_code != 200:
                raise AIProviderError(f"Gemini Embedding Error ({resp.status_code}): {resp.text}", retryable=False)

            data = resp.json()
            embedding_vals = data.get("embedding", {}).get("values", [])
            if not embedding_vals:
                raise AIProviderError("Empty embedding returned from Gemini", retryable=False)

            usage = {"prompt_tokens": len(text) // 4, "completion_tokens": 0}
            return embedding_vals, usage

        except AIProviderError:
            raise
        except Exception as e:
            logger.error(f"Gemini embedding error: {e}", exc_info=True)
            raise AIProviderError(f"Gemini embedding failed: {e}", retryable=False)

class OpenAILikeProvider(AIProvider):
    def __init__(self, api_key: str, base_url: str = None, model: str = None, embedding_model: str = None):
        import openai
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self._model = model or settings.OPENAI_MODEL
        self._embedding_model = embedding_model or settings.OPENAI_EMBEDDING_MODEL

    @property
    def model_name(self) -> str:
        return self._model
        
    @property
    def embedding_model_name(self) -> str:
        return self._embedding_model

    def generate_structured(self, prompt: str, schema_cls: Type[T], system_prompt: str = "") -> tuple[T, dict]:
        import openai
        schema_json = schema_cls.model_json_schema()
        try:
            response = self.client.chat.completions.create(
                model=self._model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt + f"\n\nOutput strictly valid JSON matching this schema:\n{json.dumps(schema_json)}"},
                    {"role": "user", "content": prompt}
                ]
            )
            raw_text = response.choices[0].message.content
            instance = schema_cls.model_validate_json(raw_text)
            
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens
            }
            return instance, usage
            
        except openai.RateLimitError as e:
            raise AIProviderError(str(e), retryable=True)
        except openai.APIConnectionError as e:
            raise AIProviderError(str(e), retryable=True)
        except Exception as e:
            raise AIProviderError(f"OpenAI error: {e}", retryable=False)

    def generate_embeddings(self, text: str) -> tuple[List[float], dict]:
        import openai
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self._embedding_model
            )
            usage = {"prompt_tokens": response.usage.prompt_tokens, "completion_tokens": 0}
            return response.data[0].embedding, usage
        except openai.RateLimitError as e:
            raise AIProviderError(str(e), retryable=True)
        except Exception as e:
            raise AIProviderError(str(e), retryable=False)

def get_ai_provider() -> AIProvider:
    provider_type = (settings.AI_PROVIDER or "gemini").lower()
    
    if provider_type in ["gemini", "google"]:
        gemini_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY") or settings.OPENAI_API_KEY
        if gemini_key:
            return GeminiProvider(api_key=gemini_key)
            
    if provider_type == "openai":
        openai_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        if openai_key:
            return OpenAILikeProvider(api_key=openai_key)
            
    return MockProvider()
