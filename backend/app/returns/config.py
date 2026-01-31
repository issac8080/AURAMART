from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        env_file_encoding='utf-8',
        extra='ignore'  # Ignore extra fields in .env file that aren't defined in Settings
    )
    
    sqlite_url: str = "sqlite:///./returns.db"
    chroma_persist_dir: str = "./chroma_db"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    policy_collection_name: str = "returns_policies"
    
    physical_confidence_threshold: float = 0.60
    description_similarity_threshold: float = 0.50
    
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    openai_max_tokens: int = 500
    openai_temperature: float = 0.3
    
    # OPIK tracing configuration
    opik_api_key: Optional[str] = None
    opik_workspace: Optional[str] = None
    opik_project_name: Optional[str] = None


settings = Settings()

if not settings.openai_api_key:
    settings.openai_api_key = os.getenv("OPENAI_API_KEY")
