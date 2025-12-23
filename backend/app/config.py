from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str
    
    # Groq API (primary LLM provider)
    groq_api_key: Optional[str] = None
    
    # Apify API (Facebook scraping)
    apify_api_token: Optional[str] = None
    
    # Legacy APIs (kept for backward compatibility)
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    
    # Facebook credentials (not used with Apify)
    facebook_email: Optional[str] = None
    facebook_password: Optional[str] = None
    
    # Environment settings
    environment: str = "development"
    
    # QA thresholds
    max_qa_retries: int = 3
    qa_readability_threshold: int = 70
    qa_coherence_threshold: int = 75
    qa_redundancy_threshold: int = 30
    qa_neutrality_threshold: int = 70
    qa_human_likeness_threshold: int = 75

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra env variables


settings = Settings()
