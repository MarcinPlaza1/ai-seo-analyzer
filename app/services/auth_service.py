from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.services.user_service import UserService
from app.core.security import SecurityService, verify_password
from app.models.user import User
from app.core.redis_client import redis_client

class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_service = UserService(db)
        self.security_service = SecurityService()

    async def authenticate_user(self, email: str, password: str) -> dict:
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        # Sprawdź czy użytkownik nie jest zablokowany
        if user.blocked_until and user.blocked_until > datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account temporarily blocked. Try again later."
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account not activated"
            )

        if not verify_password(password, user.hashed_password):
            await self.user_service.handle_failed_login(user)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        # Reset prób logowania po udanym logowaniu
        await self.user_service.reset_login_attempts(user)
        
        # Generuj tokeny
        return self.security_service.create_tokens(user.id)

    async def logout(self, refresh_token: str) -> None:
        self.security_service.invalidate_refresh_token(refresh_token) 