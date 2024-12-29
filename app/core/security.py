from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.settings import settings
from app.core.database import get_db
import logging

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")
logger = logging.getLogger(__name__)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Weryfikacja hasła"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashowanie hasła"""
    return pwd_context.hash(password)

class SecurityService:
    """Serwis obsługujący bezpieczeństwo"""
    def __init__(self):
        self.token_store: Dict[str, Dict[str, Any]] = {}
        self.access_token_expire = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        self.refresh_token_expire = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    def create_access_token(self, data: dict) -> str:
        """Tworzenie tokenu dostępu"""
        to_encode = data.copy()
        expire = datetime.utcnow() + self.access_token_expire
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    def create_refresh_token(self, user_id: int) -> str:
        """Tworzenie tokenu odświeżania"""
        refresh_token = jwt.encode(
            {"sub": str(user_id)},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        expire = datetime.utcnow() + self.refresh_token_expire
        self.token_store[refresh_token] = {"user_id": user_id, "exp": expire}
        return refresh_token
    
    def verify_refresh_token(self, refresh_token: str) -> Optional[int]:
        """Weryfikacja tokenu odświeżania"""
        token_data = self.token_store.get(refresh_token)
        if not token_data:
            return None
        
        if datetime.utcnow() > token_data["exp"]:
            del self.token_store[refresh_token]
            return None
        
        return token_data["user_id"]
    
    def create_tokens(self, user_id: int) -> dict:
        """Tworzenie pary tokenów"""
        access_token = self.create_access_token({"sub": str(user_id)})
        refresh_token = self.create_refresh_token(user_id)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    async def refresh_access_token(self, refresh_token: str) -> str:
        """Odświeżanie tokenu dostępu"""
        user_id = self.verify_refresh_token(refresh_token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        return self.create_access_token({"sub": str(user_id)})
    
    def _check_json_xss(self, data: dict) -> bool:
        """Sprawdza czy w danych JSON nie ma potencjalnego XSS"""
        def check_value(value: Any) -> bool:
            if isinstance(value, str):
                # Proste sprawdzenie tagów HTML i skryptów
                suspicious = ["<script", "javascript:", "onerror=", "onload="]
                return any(s in value.lower() for s in suspicious)
            elif isinstance(value, dict):
                return any(check_value(v) for v in value.values())
            elif isinstance(value, list):
                return any(check_value(v) for v in value)
            return False
        
        return check_value(data)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Pobieranie aktualnego użytkownika na podstawie tokenu"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    from app.models.user import User  # Import przeniesiony tutaj aby uniknąć cyklicznego importu
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user = Depends(get_current_user)):
    """Pobieranie aktywnego użytkownika"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user 