from typing import Any
from app.core.database import SessionLocal
from app.core.error_handling import ServiceError

class BaseService:
    def __init__(self):
        self.db = SessionLocal()
    
    async def handle_error(self, error: Exception) -> None:
        """Centralna obsługa błędów dla serwisów"""
        if isinstance(error, ServiceError):
            raise error
        raise ServiceError(str(error)) 