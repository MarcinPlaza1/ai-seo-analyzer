import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from typing import AsyncGenerator
from app.main import app
from app.core.database import Base, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from unittest.mock import patch
import os
import logging
from contextvars import ContextVar
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.middleware.security import SecurityMiddleware
from app.models.user import UserRole, SubscriptionTier
from app.core.permissions import require_role, require_subscription
from datetime import datetime

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Zmienne kontekstowe dla testów
test_db_var = ContextVar("test_db", default=None)
session_context = ContextVar("session_context", default=None)

# Używamy bazy danych w pamięci dla testów
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=True  # Włączamy logowanie SQL
)

# Tworzymy fabrykę sesji
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_test_db():
    try:
        db = session_context.get()
        if db is None:
            db = TestingSessionLocal()
            session_context.set(db)
        yield db
    finally:
        pass  # Nie zamykamy sesji, ponieważ jest zarządzana przez fixture test_db

@pytest.fixture(scope="session", autouse=True)
def create_test_database():
    logger.info("Creating test database...")
    Base.metadata.create_all(bind=engine)
    yield
    logger.info("Dropping test database...")
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def test_db():
    logger.info("Setting up test database session...")
    connection = engine.connect()
    transaction = connection.begin()
    
    session = TestingSessionLocal(bind=connection)
    session_context.set(session)
    
    # Nadpisujemy zależność bazy danych na wersję testową
    app.dependency_overrides[get_db] = get_test_db
    
    yield session
    
    logger.info("Cleaning up test database session...")
    session_context.set(None)  # Czyścimy kontekst sesji
    session.close()
    transaction.rollback()
    connection.close()

class MockRedis:
    def __init__(self, *args, **kwargs):
        self.data = {}
        self.expiry = {}
    
    def get(self, key):
        if key in self.expiry and self.expiry[key] < datetime.now().timestamp():
            del self.data[key]
            del self.expiry[key]
            return None
        return self.data.get(key)
    
    def set(self, key, value, ex=None, *args, **kwargs):
        self.data[key] = value
        if ex:
            self.expiry[key] = datetime.now().timestamp() + ex
        return True
        
    def incr(self, key):
        if key not in self.data:
            self.data[key] = 1
        else:
            self.data[key] = int(self.data[key]) + 1
        return self.data[key]
        
    def expire(self, key, seconds):
        self.expiry[key] = datetime.now().timestamp() + seconds
        return True

class MockLimiter:
    def __init__(self, *args, **kwargs):
        pass

    async def __call__(self, *args, **kwargs):
        return True

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    # Mockujemy Redis i rate limiter dla testów
    with patch('app.middleware.security.redis_client', MockRedis()), \
         patch('redis.Redis', return_value=MockRedis()), \
         patch('app.middleware.security.limiter', MockLimiter()):
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client 

@pytest.fixture
def client(security_app):
    """Fixture z klientem testowym"""
    with patch('app.middleware.security.redis_client', MockRedis()):
        with patch('app.middleware.security.limiter', MockLimiter()):
            return TestClient(security_app)

@pytest.fixture
def security_app():
    """Fixture z aplikacją z middleware bezpieczeństwa"""
    test_app = FastAPI()
    
    # Dodajemy endpointy testowe
    @test_app.get("/api/v1/test")
    def test_endpoint():
        return {"message": "test"}
        
    @test_app.post("/api/v1/test")
    def test_post_endpoint(data: dict):
        return {"message": "test"}
        
    @test_app.get("/api/v1/protected")
    def protected_endpoint():
        return {"message": "protected"}
        
    @test_app.post("/api/v1/upload")
    def upload_endpoint(file: bytes):
        return {"message": "uploaded"}
        
    @test_app.get("/api/v1/users")
    def users_endpoint(query: str = None):
        return {"users": []}

    @test_app.post("/api/v1/auth/register")
    async def register(request: Request):
        data = await request.json()
        if not all(k in data for k in ["email", "password", "full_name"]):
            return JSONResponse(
                status_code=400,
                content={"detail": "Missing required fields"}
            )
        return {"message": "User registered successfully"}

    @test_app.post("/api/v1/auth/login")
    async def login(request: Request):
        data = await request.json()
        if not all(k in data for k in ["email", "password"]):
            return JSONResponse(
                status_code=400,
                content={"detail": "Missing required fields"}
            )
        return {"access_token": "test_token", "token_type": "bearer"}

    @test_app.get("/api/v1/admin/test")
    @require_role(UserRole.ADMIN)
    async def admin_test():
        return {"message": "admin only"}

    @test_app.get("/api/v1/premium/test")
    @require_subscription(SubscriptionTier.PREMIUM)
    async def premium_test():
        return {"message": "premium only"}

    test_app.add_middleware(SecurityMiddleware)
    return test_app 