from typing import Optional, Dict
from fastapi import HTTPException
from celery.exceptions import TaskError
import logging

logger = logging.getLogger(__name__)

async def notify_monitoring_system(error_details: Dict) -> None:
    """Wysyła powiadomienie o błędzie do systemu monitoringu"""
    # TODO: Zaimplementuj integrację z systemem monitoringu
    logger.error(f"Error notification: {error_details}")

class SEOAuditError(Exception):
    def __init__(self, message: str, error_code: str, details: Optional[Dict] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

class TaskExecutionError(SEOAuditError):
    pass

class ValidationError(SEOAuditError):
    pass

class ResourceNotFoundError(SEOAuditError):
    pass

class AuditNotFound(ResourceNotFoundError):
    def __init__(self, audit_id: int):
        super().__init__(
            message=f"Audit with ID {audit_id} not found",
            error_code="AUDIT_NOT_FOUND",
            details={"audit_id": audit_id}
        )

async def handle_task_error(task_name: str, exc: Exception) -> Dict:
    """Centralna obsługa błędów dla zadań Celery"""
    error_details = {
        'task_name': task_name,
        'error_type': exc.__class__.__name__,
        'error_message': str(exc)
    }
    
    # Logowanie błędu
    logger.error(f"Task error in {task_name}", extra=error_details)
    
    # Notyfikacja do systemu monitoringu
    await notify_monitoring_system(error_details)
    
    return error_details