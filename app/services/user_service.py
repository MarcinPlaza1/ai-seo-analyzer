from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import get_password_hash, verify_password
from app.core.email import EmailService
from datetime import datetime, timedelta
import secrets

class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.email_service = EmailService()
        self.max_login_attempts = 5
        self.block_duration = timedelta(minutes=15)

    async def create_user(self, user_data: UserCreate) -> User:
        # Sprawdź czy użytkownik już istnieje
        if self.db.query(User).filter(User.email == user_data.email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Tworzenie nowego użytkownika
        activation_token = secrets.token_urlsafe(32)
        user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=get_password_hash(user_data.password),
            is_active=False,  # Użytkownik jest domyślnie nieaktywny
            activation_token=activation_token,
            login_attempts=0
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        # Wysyłanie emaila aktywacyjnego
        await self.email_service.send_activation_email(user.email, activation_token)
        
        return user

    async def activate_user(self, token: str) -> bool:
        user = self.db.query(User).filter(
            User.activation_token == token,
            User.is_active == False
        ).first()
        
        if not user:
            return False
            
        user.is_active = True
        user.activation_token = None
        self.db.commit()
        return True

    async def reset_password_request(self, email: str) -> None:
        user = self.db.query(User).filter(User.email == email).first()
        if user:
            reset_token = secrets.token_urlsafe(32)
            user.reset_token = reset_token
            user.reset_token_expires = datetime.utcnow() + timedelta(hours=24)
            self.db.commit()
            
            await self.email_service.send_password_reset_email(
                email,
                reset_token
            )

    async def handle_failed_login(self, user: User) -> None:
        user.login_attempts += 1
        if user.login_attempts >= self.max_login_attempts:
            user.blocked_until = datetime.utcnow() + self.block_duration
        self.db.commit()

    async def reset_login_attempts(self, user: User) -> None:
        user.login_attempts = 0
        user.blocked_until = None
        self.db.commit() 