from fastapi import Request
from app.models.user import User
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def log_access_attempt(request: Request, user: User) -> None:
    """Loguje próbę dostępu do API"""
    logger.info(
        f"Access attempt: user_id={user.id}, "
        f"endpoint={request.url.path}, "
        f"method={request.method}, "
        f"ip={request.client.host}, "
        f"timestamp={datetime.utcnow().isoformat()}"
    ) 