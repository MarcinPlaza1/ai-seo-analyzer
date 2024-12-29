from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from sqlalchemy.orm import Session
from app.config import settings
from app.models.user import User
from app.core.database import get_db
from app.core.rate_limit import RateLimiter
from app.core.logging import log_access_attempt
from app.core.permissions import get_user_permissions
from app.core.auth import get_current_user
from typing import Optional, List

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
rate_limiter = RateLimiter()

async def verify_api_key(
    api_key: str = Depends(APIKeyHeader(name="X-API-Key"))
):
    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy klucz API"
        )

def get_current_user_with_permissions(required_permissions: Optional[List[str]] = None):
    async def current_user_with_permissions(
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ) -> User:
        # Rate limiting per user
        await rate_limiter.check_rate_limit(current_user.id)
        
        if required_permissions:
            user_permissions = get_user_permissions(current_user)
            if not all(perm in user_permissions for perm in required_permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions"
                )
        
        # Log access attempt
        await log_access_attempt(request, current_user)
        return current_user
    
    return current_user_with_permissions 