import os
from dotenv import load_dotenv
from typing import Dict, NamedTuple
from pydantic import BaseSettings

load_dotenv()

class TimeoutConfig(NamedTuple):
    connect: int
    read: int
    total: int

class RetryConfig(NamedTuple):
    max_attempts: int
    min_wait: int
    max_wait: int

class Settings(BaseSettings):
    # Timeouty dla różnych operacji
    TIMEOUTS: Dict[str, TimeoutConfig] = {
        "crawl": TimeoutConfig(3, 10, 15),
        "links": TimeoutConfig(2, 5, 8),
        "images": TimeoutConfig(2, 5, 8),
        "meta": TimeoutConfig(2, 3, 6),
        "default": TimeoutConfig(2, 5, 8)
    }
    
    # Konfiguracja retry
    RETRY_CONFIG = RetryConfig(3, 1, 10)
    
    # Timeouty dla zadań Celery
    CELERY_TIMEOUTS: Dict[str, int] = {
        "crawl": 600,
        "links": 300,
        "images": 300,
        "meta": 180,
        "default": 300
    }

    # Konfiguracja SERP API
    SERPAPI_KEY: str = os.getenv("SERPAPI_KEY", "")
    SERPAPI_TIMEOUT: int = 30
    SERPAPI_MAX_RETRIES: int = 3

    # Konfiguracja rate limitingu
    RATE_LIMIT_WINDOW_SIZE: int = 60  # 1 minuta
    RATE_LIMIT_MAX_REQUESTS: int = 100  # maksymalna liczba requestów na minutę

    # Konfiguracja bezpieczeństwa
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    API_KEY: str = os.getenv("API_KEY", "your-api-key")

    def get_timeout(self, operation: str) -> TimeoutConfig:
        return self.TIMEOUTS.get(operation, self.TIMEOUTS["default"])

    def get_celery_timeout(self, operation: str) -> int:
        return self.CELERY_TIMEOUTS.get(operation, self.CELERY_TIMEOUTS["default"])

settings = Settings()
