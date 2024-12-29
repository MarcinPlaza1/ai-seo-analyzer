from pydantic import BaseSettings, BaseModel
from typing import Dict, List, Optional, ClassVar
import os
from dataclasses import dataclass

class Settings(BaseSettings):
    CELERY_TIMEOUTS: ClassVar[Dict[str, int]] = {'crawl': 3600, 'default': 1800}
    
    # Ustawienia bazy danych
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "seo"
    POSTGRES_SERVER: str = "db"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Ustawienia API
    OPENAI_API_KEY: str = ""
    SERPAPI_KEY: str = ""
    
    # Ustawienia Elasticsearch
    ELASTICSEARCH_HOST: str = "localhost"
    ELASTICSEARCH_PORT: str = "9200"
    ELASTICSEARCH_USER: str = "elastic"
    ELASTICSEARCH_PASSWORD: str = "elastic"
    ELASTICSEARCH_COMPAT_VERSION: str = "7"
    
    # Ustawienia Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: str = "6379"
    REDIS_PASSWORD: Optional[str] = None
    
    # Ustawienia JWT
    SECRET_KEY: str = "your-secret-key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Ustawienia ogólne
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "SEO Tool"
    
    # Ustawienia szyfrowania
    ENCRYPTION_SALT: str = "a7815ab93775e05ec8d029274a454ab6"
    
    # Ustawienia Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings() 