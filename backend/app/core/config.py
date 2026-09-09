import os
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "KRISH AI TUTOR"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = "krish-ai-tutor-secret-key-development-mode-only"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    ALLOW_DEV_ANONYMOUS_AUTH: bool = False

    # Database
    # Default to local SQLite for instant zero-dependency execution, or PostgreSQL if configured
    DATABASE_URL: str = "sqlite+aiosqlite:///./krish_tutor.db"

    # AI Provider: "mock", "gemini", or "openai"
    AI_PROVIDER: Literal["mock", "gemini", "openai"] = "mock"
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    AI_MODEL_FAST: str = "gemini-2.5-flash"
    AI_MODEL_ADVANCED: str = "gemini-2.5-pro"

    # Embeddings & Vector Search
    EMBEDDING_MODEL: str = "text-embedding-004"
    VECTOR_SEARCH_TOP_K: int = 4
    VECTOR_SIMILARITY_THRESHOLD: float = 0.60

    # File storage
    UPLOAD_DIR: str = "./uploads"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
