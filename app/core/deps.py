from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.config import settings
from app.core.security import verify_password
from app.models.user import User
from app.schemas.user import UserInDB
from app.core.database import get_db
from datetime import datetime, timedelta
from app.core.rate_limit import RateLimiter
from app.core.permissions import get_user_permissions
from app.core.logging import log_access_attempt
from typing import Optional, List

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
rate_limiter = RateLimiter()

async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user 

async def verify_api_key(api_key: str = Depends(APIKeyHeader(name="X-API-Key"))):
    if not api_key or api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user_with_permissions(required_permissions: Optional[List[str]] = None):
    async def current_user_with_permissions(
        request: Request,
        current_user: User = Depends(get_current_user)
    ) -> User:
        # Rate limiting per user
        await rate_limiter.check_rate_limit(current_user.id)
        
        if required_permissions:
            user_permissions = await get_user_permissions(current_user.id)
            if not all(perm in user_permissions for perm in required_permissions):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not enough permissions",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
        # Log access attempt
        await log_access_attempt(request, current_user)
        return current_user
    
    return current_user_with_permissions 