from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.models.user import UserCreate
from app.core.security import SecurityService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
security_service = SecurityService()

@router.post("/register")
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    user_service = UserService(db)
    await user_service.create_user(user_data)
    return {"message": "Registration successful. Please check your email to activate account."}

@router.post("/login")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Endpoint logowania"""
    try:
        user_service = UserService(db)
        user = await user_service.authenticate_user(form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
        
        tokens = security_service.create_tokens(user.id)
        return tokens
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/logout")
async def logout(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    auth_service = AuthService(db)
    await auth_service.logout(refresh_token)
    return {"message": "Successfully logged out"} 