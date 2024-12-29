from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core import get_db, SecurityService, get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate
from datetime import datetime, timedelta
import logging

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
security_service = SecurityService()
logger = logging.getLogger(__name__)

@router.post("/register")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """Rejestracja nowego użytkownika"""
    # Sprawdź czy użytkownik już istnieje
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Stwórz nowego użytkownika
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        is_active=False  # Użytkownik musi aktywować konto
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return {"message": "User created successfully"}

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Logowanie użytkownika"""
    logger.debug(f"Próba logowania dla użytkownika: {form_data.username}")
    
    # Walidacja formatu danych
    if not form_data.username or not form_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials format"
        )
    
    # Znajdź użytkownika
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user:
        logger.warning(f"Nieudana próba logowania - użytkownik nie istnieje: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Sprawdź czy konto jest aktywne
    if not user.is_active:
        logger.warning(f"Próba logowania na nieaktywne konto: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user account"
        )
    
    # Sprawdź czy konto nie jest zablokowane
    if user.blocked_until and user.blocked_until > datetime.utcnow():
        logger.warning(f"Próba logowania na zablokowane konto: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is blocked due to too many login attempts"
        )
    
    # Sprawdź hasło
    if not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Nieudana próba logowania - nieprawidłowe hasło dla użytkownika: {form_data.username}")
        
        # Aktualizuj licznik nieudanych prób
        user.login_attempts = (user.login_attempts or 0) + 1
        user.last_login_attempt = datetime.utcnow()
        
        # Jeśli przekroczono limit prób, zablokuj konto
        if user.login_attempts >= 5:
            user.blocked_until = datetime.utcnow() + timedelta(minutes=30)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Too many login attempts. Account blocked for 30 minutes"
            )
        
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Reset licznika nieudanych prób po udanym logowaniu
    user.login_attempts = 0
    user.last_login_attempt = None
    user.blocked_until = None
    db.commit()
    
    # Wygeneruj tokeny
    tokens = security_service.create_tokens(user.id)
    logger.info(f"Udane logowanie dla użytkownika: {form_data.username}")
    return tokens 