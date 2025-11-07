from pydantic_settings import BaseSettings
from typing import List
from pathlib import Path
import os

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://raguser:ragpass@localhost:5432/ragdb")
    
    APP_NAME: str = "RAG Chatbot API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10485760
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".txt", ".md"]
    
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", 500))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", 100))

    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", 1536))
    
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", 0.7))
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", 800))
    
    TOP_K_RESULTS: int = int(os.getenv("TOP_K_RESULTS", 3))
    MIN_SIMILARITY: float = float(os.getenv("MIN_SIMILARITY", 0.5))

    class Config:
        env_file = ".env"
        case_sensitive = True
        
    @property
    def UPLOAD_DIR_PATH(self) -> Path:
        """Get upload directory as Path object"""
        path = Path(self.UPLOAD_DIR)
        path.mkdir(exist_ok=True)
        return path

settings = Settings()
