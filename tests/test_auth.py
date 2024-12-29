import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator, Any, cast, Dict
from _pytest.fixtures import FixtureFunction
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status, Depends
from fastapi.testclient import TestClient
from httpx import AsyncClient
import unittest.mock
from jose import jwt
from sqlalchemy.orm import Session, sessionmaker

from app.core.security import SecurityService, verify_password
from app.config.settings import settings
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.database import Base, get_db
from sqlalchemy import create_engine
import os
from app.core.deps import get_current_user, get_current_active_user
from app.services.user_service import UserService
from app.core.email import EmailService

# Konfiguracja testowej bazy danych
TEST_DATABASE_URL = "sqlite:///./test.db"

@pytest_asyncio.fixture(scope="function")
async def test_db() -> AsyncGenerator:
    """Fixture dostarczający testową bazę danych SQLite."""
    engine = create_engine(TEST_DATABASE_URL)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        if os.path.exists("./test.db"):
            os.remove("./test.db")

@pytest.fixture(scope="function")
def security_service() -> SecurityService:
    """Fixture dostarczający serwis bezpieczeństwa."""
    return SecurityService()

@pytest.fixture(scope="function")
def active_user() -> User:
    """Fixture dostarczający aktywnego użytkownika."""
    return User(
        email="test@example.com",
        full_name="Test User",
        hashed_password="hashed_password123",
        is_active=True
    )

@pytest.fixture(scope="function")
def inactive_user() -> User:
    """Fixture dostarczający nieaktywnego użytkownika."""
    return User(
        email="inactive@example.com",
        full_name="Inactive User",
        hashed_password="hashed_password123",
        is_active=False
    )

@pytest.fixture(scope="function")
def mock_email_service() -> Generator[unittest.mock.MagicMock, None, None]:
    """Fixture dostarczający zamockowany serwis email."""
    with unittest.mock.patch('app.services.user_service.EmailService') as mock:
        mock.return_value.send_activation_email = unittest.mock.AsyncMock()
        mock.return_value.send_password_reset_email = unittest.mock.AsyncMock()
        mock.return_value.send_email = unittest.mock.AsyncMock()
        yield mock

class TestTokens:
    """Testy związane z tokenami JWT."""
    
    @pytest.mark.asyncio
    async def test_create_tokens_success(self, security_service, active_user):
        """Test tworzenia tokenów dla aktywnego użytkownika."""
        tokens = security_service.create_tokens(active_user.id)
        
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens.get("token_type") == "bearer"
        
        payload = jwt.decode(
            tokens.get("access_token"), 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": False}
        )
        assert str(active_user.id) == payload["sub"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("refresh_token,expected_error", [
        ("invalid_token", "Invalid or expired refresh token"),
        ("", "Invalid or expired refresh token"),
        (None, "Invalid or expired refresh token"),
    ])
    async def test_refresh_token_invalid(
        self, security_service, refresh_token, expected_error
    ):
        """Test obsługi nieprawidłowych tokenów odświeżania."""
        with pytest.raises(HTTPException) as exc_info:
            await security_service.refresh_access_token(refresh_token)
        
        assert exc_info.value.detail == expected_error
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, security_service, active_user):
        """Test pomyślnego odświeżenia tokenu dostępu."""
        active_user.id = 1
        tokens = security_service.create_tokens(active_user.id)
        new_access_token = await security_service.refresh_access_token(tokens.get("refresh_token"))
        
        payload = jwt.decode(
            new_access_token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": False}
        )
        assert str(active_user.id) == payload["sub"]

    @pytest.mark.asyncio
    async def test_token_expiration(self, security_service, active_user):
        """Test wygasania tokenu po określonym czasie."""
        # Tworzymy token z krótkim czasem wygaśnięcia
        expire_delta = timedelta(seconds=30)
        security_service.access_token_expire = expire_delta
        
        # Ustalamy bazowy czas
        current_time = datetime.now(timezone.utc)
        token = security_service.create_access_token({"sub": str(active_user.id)})
        
        # Dekodujemy token bez weryfikacji czasu wygaśnięcia
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": False}
        )
        
        # Sprawdzamy czy token ma ustawiony czas wygaśnięcia
        assert "exp" in payload
        
        # Sprawdzamy czy czas wygaśnięcia jest w przyszłości
        exp = datetime.fromtimestamp(payload["exp"], timezone.utc)
        diff = exp - current_time
        
        # Sprawdzamy czy różnica czasu jest bliska 30 sekundom (z marginesem 5 sekund)
        assert 25 <= diff.total_seconds() <= 35

class TestAuthentication:
    """Testy związane z uwierzytelnianiem użytkowników."""

    def test_verify_password(self):
        """Test weryfikacji hasła."""
        # Używamy prostszego hashu do testów
        password = "test_password"
        hashed = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LedYQNB8UHUHzhxlu"
        
        # Mockujemy funkcję weryfikacji hasła
        with unittest.mock.patch('app.core.security.pwd_context.verify', return_value=True):
            assert verify_password(password, hashed)
        
        with unittest.mock.patch('app.core.security.pwd_context.verify', return_value=False):
            assert not verify_password("wrong_password", hashed)

    @pytest.mark.asyncio
    @unittest.mock.patch('app.core.security.jwt.decode')
    async def test_get_current_user_success(
        self, mock_jwt_decode, test_db, active_user
    ):
        """Test pobierania aktywnego użytkownika na podstawie tokenu."""
        test_db.add(active_user)
        test_db.commit()
        
        mock_jwt_decode.return_value = {"sub": str(active_user.id)}
        
        with unittest.mock.patch('app.core.database.get_db', return_value=test_db):
            user = await get_current_user(test_db, "valid_token")
            assert user.id == active_user.id
            assert user.is_active == True

    @pytest.mark.asyncio
    @unittest.mock.patch('app.core.security.jwt.decode')
    async def test_get_current_user_invalid_token(
        self, mock_jwt_decode, test_db
    ):
        """Test obsługi nieprawidłowego tokenu."""
        mock_jwt_decode.side_effect = jwt.JWTError()
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("invalid_token", test_db)
        
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_active_user_inactive(
        self, test_db, inactive_user
    ):
        """Test obsługi nieaktywnego użytkownika."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(inactive_user)
        
        assert exc_info.value.status_code == 400
        assert "Inactive user" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_active_user_success(
        self, test_db, active_user
    ):
        """Test pobierania aktywnego użytkownika."""
        user = await get_current_active_user(active_user)
        assert user.id == active_user.id
        assert user.is_active == True

class TestSecurityService:
    """Testy dla podstawowych operacji na tokenach."""
    
    def test_create_access_token(self, security_service):
        """Test tworzenia access tokena."""
        user_id = 1
        token = security_service.create_access_token({"sub": str(user_id)})
        
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": False}
        )
        assert str(user_id) == payload["sub"]
        assert "exp" in payload

    def test_create_refresh_token(self, security_service):
        """Test tworzenia refresh tokena."""
        user_id = 1
        refresh_token = security_service.create_refresh_token(user_id)
        
        assert refresh_token in security_service.token_store
        assert security_service.token_store[refresh_token]["user_id"] == user_id # type: ignore

    def test_verify_refresh_token_valid(self, security_service):
        """Test weryfikacji poprawnego refresh tokena."""
        user_id = 1
        refresh_token = security_service.create_refresh_token(user_id)
        
        verified_user_id = security_service.verify_refresh_token(refresh_token)
        assert verified_user_id == user_id

    def test_verify_refresh_token_invalid(self, security_service):
        """Test weryfikacji niepoprawnego refresh tokena."""
        assert security_service.verify_refresh_token("invalid_token") is None

class TestUserService:
    """Testy dla operacji związanych z użytkownikami."""
    
    @pytest.mark.asyncio
    async def test_create_user_success(self, test_db, mock_email_service):
        """Test pomyślnego utworzenia użytkownika."""
        user_service = UserService(test_db)
        user_data = UserCreate(
            email="new@example.com",
            password="strong_password123",
            full_name="Test User"
        )
        
        user = await user_service.create_user(user_data)
        assert user.email == user_data.email
        assert user.is_active == False
        assert user.activation_token is not None
        mock_email_service.return_value.send_activation_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, test_db, active_user):
        """Test próby utworzenia użytkownika z istniejącym emailem."""
        test_db.add(active_user)
        test_db.commit()
        
        user_service = UserService(test_db)
        user_data = UserCreate(
            email=active_user.email,
            password="password123",
            full_name="Duplicate User"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await user_service.create_user(user_data)
        assert exc_info.value.status_code == 400
        assert "Email already registered" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_activate_user_success(self, test_db):
        """Test aktywacji użytkownika."""
        user_service = UserService(test_db)
        user_data = UserCreate(
            email="activate@example.com",
            password="password123",
            full_name="Activate User"
        )
        
        user = await user_service.create_user(user_data)
        assert await user_service.activate_user(user.activation_token) == True
        
        activated_user = test_db.query(User).filter_by(id=user.id).first()
        assert activated_user.is_active == True
        assert activated_user.activation_token is None

    @pytest.mark.asyncio
    async def test_handle_failed_login(self, test_db, active_user):
        """Test obsługi nieudanych prób logowania."""
        user_service = UserService(test_db)
        test_db.add(active_user)
        test_db.commit()
        
        # Symuluj kilka nieudanych prób
        for _ in range(4):
            await user_service.handle_failed_login(active_user)
        assert active_user.login_attempts == 4
        assert active_user.blocked_until is None
        
        # Ostatnia próba powinna zablokować konto
        await user_service.handle_failed_login(active_user)
        assert active_user.login_attempts == 5
        assert active_user.blocked_until is not None

@pytest.mark.asyncio
async def test_register_invalid_data(async_client: AsyncClient, test_db: Session) -> None:
    """Test rejestracji z nieprawidłowymi danymi"""
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "",  # pusty email
            "password": "short",  # za krótkie hasło
            "full_name": "Test User"
        }
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    response_json: Dict[str, Any] = response.json()
    assert "detail" in response_json

@pytest.mark.asyncio
async def test_login_blocked_user(async_client: AsyncClient, test_db: Session) -> None:
    """Test logowania zablokowanego użytkownika"""
    user = User(
        email="blocked@example.com",
        full_name="Blocked User",
        hashed_password="hashed_password",
        is_active=True,
        login_attempts=5,
        blocked_until=datetime.utcnow() + timedelta(minutes=30)
    )
    test_db.add(user)
    test_db.commit()

    response = await async_client.post(
        "/api/v1/auth/login",
        data={
            "username": "blocked@example.com",
            "password": "testpassword"
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    response_json: Dict[str, Any] = response.json()
    assert "account is blocked" in str(response_json.get("detail", "")).lower()

@pytest.mark.asyncio
async def test_login_inactive_user(async_client: AsyncClient, test_db: Session) -> None:
    """Test logowania nieaktywnego użytkownika"""
    user = User(
        email="inactive@example.com",
        full_name="Inactive User",
        hashed_password="hashed_password",
        is_active=False
    )
    test_db.add(user)
    test_db.commit()

    response = await async_client.post(
        "/api/v1/auth/login",
        data={
            "username": "inactive@example.com",
            "password": "testpassword"
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    response_json: Dict[str, Any] = response.json()
    assert "inactive" in str(response_json.get("detail", "")).lower()

@pytest.mark.asyncio
async def test_login_invalid_password_format(async_client: AsyncClient, test_db: Session) -> None:
    """Test logowania z nieprawidłowym formatem hasła"""
    response = await async_client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": ""  # puste hasło
        }
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    response_json: Dict[str, Any] = response.json()
    assert "validation error" in str(response_json.get("detail", "")).lower()

@pytest.mark.asyncio
async def test_register_duplicate_email(async_client: AsyncClient, test_db: Session) -> None:
    """Test rejestracji z już istniejącym emailem"""
    user_data = {
        "email": "duplicate@example.com",
        "password": "testpassword123",
        "full_name": "Test User"
    }
    
    response1 = await async_client.post("/api/v1/auth/register", json=user_data)
    assert response1.status_code == status.HTTP_200_OK
    
    response2 = await async_client.post("/api/v1/auth/register", json=user_data)
    assert response2.status_code == status.HTTP_400_BAD_REQUEST
    response_json: Dict[str, Any] = response2.json()
    assert "email already registered" in str(response_json.get("detail", "")).lower()

@pytest.mark.asyncio
async def test_login_rate_limit(async_client: AsyncClient, test_db: Session) -> None:
    """Test ograniczenia prób logowania"""
    user = User(
        email="ratelimit@example.com",
        full_name="Rate Limit User",
        hashed_password="hashed_password",
        is_active=True,
        login_attempts=0
    )
    test_db.add(user)
    test_db.commit()

    for _ in range(6):  # Przekraczamy limit 5 prób
        response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": "ratelimit@example.com",
                "password": "wrongpassword"
            }
        )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    response_json: Dict[str, Any] = response.json()
    assert "too many login attempts" in str(response_json.get("detail", "")).lower()