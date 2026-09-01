from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "postgresql://recruit_admin:recruit_password@localhost:5433/recruit_db"
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_PRE_PING: bool = True
    DB_POOL_RECYCLE: int = 1800

    # Queue & Async Workers
    REDIS_URL: str = "redis://localhost:6379/0"
    QUEUE_BACKEND: str = "local" # "local", "redis", or "celery"

    # Security & Auth
    SECRET_KEY: str = "temporary-secret-do-not-use-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Specific CORS origins to prevent wildcard exfiltration when credentials are enabled
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://talentai-recruiter.vercel.app"
    ]

    # Rate Limiting
    RATE_LIMIT_DEFAULT: str = "60/minute"
    RATE_LIMIT_AI_ENDPOINTS: str = "15/minute"

    # AI Configuration (OpenAI & Google Gemini)
    AI_PROVIDER: str = "gemini" # "gemini", "openai", or "mock"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.6-flash"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # External APIs & Sourcing
    GITHUB_TOKEN: Optional[str] = None

    # Search & Retrieval Weights
    RETRIEVAL_WEIGHT_SKILL: float = 0.4
    RETRIEVAL_WEIGHT_SEMANTIC: float = 0.3
    RETRIEVAL_WEIGHT_EXPERIENCE: float = 0.2
    RETRIEVAL_WEIGHT_PREFERRED: float = 0.1
    RETRIEVAL_TOP_K: int = 50
    RERANK_TOP_N: int = 5
    RERANK_CONCURRENCY: int = 5

    # Storage & Uploads
    STORAGE_BACKEND: str = "supabase" # "supabase", "local", "s3", or "gcs"
    S3_BUCKET_NAME: Optional[str] = None
    S3_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    GCS_BUCKET_NAME: Optional[str] = None
    MAX_CV_FILE_SIZE_MB: int = 50
    ALLOWED_CV_EXTENSIONS: List[str] = [".pdf", ".docx", ".doc", ".txt"]

    # Antivirus Security
    CLAMAV_ENABLED: bool = False
    CLAMAV_HOST: str = "localhost"
    CLAMAV_PORT: int = 3310

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_prod_database_url(cls, v: str, info) -> str:
        env = info.data.get("ENVIRONMENT", "development")
        if env == "production" and "recruit_password" in v:
            raise ValueError("Default database password cannot be used in production environment.")
        return v

settings = Settings()
