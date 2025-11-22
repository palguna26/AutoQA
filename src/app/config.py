"""Configuration management using pydantic-settings."""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # GitHub App Configuration
    github_app_id: str
    github_private_key: str
    github_webhook_secret: str
    
    # Database Configuration
    database_url: str
    
    @field_validator('database_url')
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        """Normalize database URL to use asyncpg driver for async SQLAlchemy.
        
        Render and other providers often give postgresql:// URLs which default to psycopg2.
        We need postgresql+asyncpg:// for async SQLAlchemy.
        """
        if v and v.startswith('postgresql://'):
            return v.replace('postgresql://', 'postgresql+asyncpg://', 1)
        elif v and v.startswith('postgres://'):
            return v.replace('postgres://', 'postgresql+asyncpg://', 1)
        return v
    
    # Redis Configuration (optional)
    redis_url: Optional[str] = "redis://localhost:6379/0"
    
    # LLM Configuration
    llm_provider: str = "none"  # none, groq, openai
    llm_api_key: Optional[str] = None
    
    # Feature Flags
    auto_merge_enabled: bool = False
    
    # Server Configuration
    port: int = 8000
    debug: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

