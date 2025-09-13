import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR}/bazaarhub.db"
    
    # Redis configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    
    # Rate limiting configuration
    RATE_LIMIT_LIKES_PER_MINUTE: int = 60  # Maximum likes per minute per user
    RATE_LIMIT_LIKES_PER_HOUR: int = 300   # Maximum likes per hour per user
    
    # For production, uncomment and configure PostgreSQL
    # DATABASE_URL = "postgresql+asyncpg://user:password@localhost/bazaarhub"
    
    class Config:
        env_file = ".env"

settings = Settings()