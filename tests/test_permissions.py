import pytest
from httpx import AsyncClient
import pytest_asyncio
from datetime import datetime, timedelta
from app.main import app
from app.models.user import User, UserRole, SubscriptionTier
from app.core.security import SecurityService, get_password_hash
from sqlalchemy.orm import Session
from typing import AsyncGenerator, Dict, Any
from fastapi import HTTPException, status
from app.models.audit import Audit
from app.core.permissions import require_role, require_subscription, check_permissions

@pytest.mark.asyncio
async def test_analyze_with_ai_permissions(async_client: AsyncClient, test_db: Session) -> None:
    """
    Sprawdza wymagania:
    1. Użytkownik musi mieć rolę User lub wyższą.
    2. Użytkownik musi mieć aktywną subskrypcję Premium.
    """

    # Tworzenie użytkownika z darmową subskrypcją
    free_user = User(
        email="free_user@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Free User",
        role=UserRole.USER,
        subscription_tier=SubscriptionTier.FREE,
        subscription_end=None,
        is_active=True
    )
    test_db.add(free_user)
    test_db.commit()
    test_db.refresh(free_user)

    # Tworzenie użytkownika z premium
    premium_user = User(
        email="premium_user@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Premium User",
        role=UserRole.USER,
        subscription_tier=SubscriptionTier.PREMIUM,
        subscription_end=datetime.utcnow() + timedelta(days=30),
        is_active=True
    )
    test_db.add(premium_user)
    test_db.commit()
    test_db.refresh(premium_user)

    security_service = SecurityService()

    # Test dla użytkownika z darmową subskrypcją
    free_token = security_service.create_access_token({"sub": str(free_user.id)})
    free_headers = {"Authorization": f"Bearer {free_token}"}
    response = await async_client.post("/api/v1/audits/1/analyze", headers=free_headers)
    assert response.status_code == 402
    response_json: Dict[str, Any] = response.json()
    assert "subskrypcja" in response_json.get("detail", "").lower()

    # Test dla użytkownika premium
    premium_token = security_service.create_access_token({"sub": str(premium_user.id)})
    premium_headers = {"Authorization": f"Bearer {premium_token}"}
    response = await async_client.post("/api/v1/audits/1/analyze", headers=premium_headers)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_require_role_inactive_user(client: AsyncClient, test_db: Session) -> None:
    """Test dekoratora require_role dla nieaktywnego użytkownika"""
    user = User(
        email="inactive@example.com",
        full_name="Inactive User",
        hashed_password="hashed_password",
        is_active=False,
        role=UserRole.USER
    )
    test_db.add(user)
    test_db.commit()

    @require_role(UserRole.USER)
    async def protected_endpoint(current_user: User) -> Dict[str, str]:
        return {"message": "success"}

    with pytest.raises(HTTPException) as exc_info:
        await protected_endpoint(current_user=user)
    
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "nieaktywne konto" in str(exc_info.value.detail).lower()

@pytest.mark.asyncio
async def test_require_role_hierarchy() -> None:
    """Test hierarchii ról"""
    user_roles = [
        (UserRole.GUEST, UserRole.USER),
        (UserRole.USER, UserRole.PREMIUM),
        (UserRole.USER, UserRole.ADMIN),
        (UserRole.PREMIUM, UserRole.ADMIN)
    ]

    for current_role, required_role in user_roles:
        user = User(
            email=f"{current_role}@example.com",
            full_name=f"{current_role} User",
            hashed_password="hashed_password",
            is_active=True,
            role=current_role
        )

        @require_role(required_role)
        async def protected_endpoint(current_user: User) -> Dict[str, str]:
            return {"message": "success"}

        with pytest.raises(HTTPException) as exc_info:
            await protected_endpoint(current_user=user)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.asyncio
async def test_require_subscription_expired(client: AsyncClient, test_db: Session) -> None:
    """Test dekoratora require_subscription dla wygasłej subskrypcji"""
    user = User(
        email="expired@example.com",
        full_name="Expired Premium User",
        hashed_password="hashed_password",
        is_active=True,
        subscription_tier=SubscriptionTier.PREMIUM,
        subscription_end=datetime.utcnow() - timedelta(days=1)
    )
    test_db.add(user)
    test_db.commit()

    @require_subscription(SubscriptionTier.PREMIUM)
    async def premium_endpoint(current_user: User) -> Dict[str, str]:
        return {"message": "success"}

    with pytest.raises(HTTPException) as exc_info:
        await premium_endpoint(current_user=user)
    assert exc_info.value.status_code == status.HTTP_402_PAYMENT_REQUIRED
    assert "wymagana aktywna subskrypcja" in str(exc_info.value.detail).lower()

@pytest.mark.asyncio
async def test_check_permissions_nonexistent_audit(client: AsyncClient, test_db: Session) -> None:
    """Test sprawdzania uprawnień dla nieistniejącego audytu"""
    user = User(
        email="test@example.com",
        full_name="Test User",
        hashed_password="hashed_password",
        is_active=True
    )
    test_db.add(user)
    test_db.commit()

    with pytest.raises(HTTPException) as exc_info:
        await check_permissions(user, audit_id=99999, db=test_db)
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "nie został znaleziony" in str(exc_info.value.detail).lower()

@pytest.mark.asyncio
async def test_check_permissions_unauthorized_access(client: AsyncClient, test_db: Session) -> None:
    """Test sprawdzania uprawnień dla nieautoryzowanego dostępu do audytu"""
    owner = User(
        email="owner@example.com",
        full_name="Owner User",
        hashed_password="hashed_password",
        is_active=True
    )
    other_user = User(
        email="other@example.com",
        full_name="Other User",
        hashed_password="hashed_password",
        is_active=True
    )
    test_db.add_all([owner, other_user])
    test_db.commit()

    audit = Audit(
        url="https://example.com",
        owner_id=owner.id
    )
    test_db.add(audit)
    test_db.commit()

    with pytest.raises(HTTPException) as exc_info:
        await check_permissions(other_user, audit_id=audit.id, db=test_db)
    
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "brak dostępu" in str(exc_info.value.detail).lower()