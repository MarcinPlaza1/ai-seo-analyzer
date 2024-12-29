from typing import Optional, List
from fastapi import HTTPException, status, Depends, Request
from fastapi.responses import JSONResponse
from app.models.user import User, UserRole, SubscriptionTier
from app.models.audit import Audit
from sqlalchemy.orm import Session
from functools import wraps
from typing import List, Optional, Callable
from app.core.auth import get_current_user

def get_user_permissions(user: User) -> List[str]:
    """Pobiera uprawnienia użytkownika"""
    if not user:
        return []
    return user.get_permissions()

def require_role(required_role: UserRole):
    """Dekorator sprawdzający rolę użytkownika"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            if not current_user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nieaktywne konto użytkownika"
                )
            
            roles_hierarchy = {
                UserRole.GUEST: 0,
                UserRole.USER: 1,
                UserRole.PREMIUM: 2,
                UserRole.ADMIN: 3
            }
            
            if roles_hierarchy[current_user.role] < roles_hierarchy[required_role]:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Niewystarczające uprawnienia"}
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

def require_subscription(required_tier: SubscriptionTier):
    """Dekorator sprawdzający poziom subskrypcji"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            if not current_user.is_subscription_active():
                return JSONResponse(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    content={
                        "detail": "Wymagana aktywna subskrypcja",
                        "code": "subscription_required"
                    }
                )
            
            tiers_hierarchy = {
                SubscriptionTier.FREE: 0,
                SubscriptionTier.PREMIUM: 1,
                SubscriptionTier.ENTERPRISE: 2
            }
            
            if tiers_hierarchy[current_user.subscription_tier] < tiers_hierarchy[required_tier]:
                return JSONResponse(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    content={
                        "detail": "Wymagana subskrypcja premium",
                        "code": "subscription_upgrade_required"
                    }
                )
            
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

async def check_permissions(user: User, audit_id: int, db: Session) -> Optional[Audit]:
    """Sprawdza uprawnienia użytkownika do dostępu do audytu"""
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit o ID {audit_id} nie został znaleziony"
        )
    
    if audit.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak dostępu do tego audytu"
        )
    
    return audit 