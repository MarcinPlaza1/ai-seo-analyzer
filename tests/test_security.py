import pytest
from fastapi import FastAPI, HTTPException, status, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import json
import time
from typing import Generator, Any

from app.middleware.security import SecurityMiddleware
from app.models.user import User, UserRole, SubscriptionTier
from app.core.security import SecurityService
from app.core.permissions import require_role, require_subscription
from app.main import app
from app.core.settings import settings

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

@pytest.fixture
def security_app() -> FastAPI:
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

@pytest.fixture
def client(security_app: FastAPI) -> TestClient:
    """Fixture z klientem testowym"""
    with patch('app.middleware.security.redis_client', MockRedis()):
        with patch('app.middleware.security.limiter', MockLimiter()):
            return TestClient(security_app)

@pytest.fixture
def mock_redis() -> MockRedis:
    """Fixture mockujący Redis"""
    return MockRedis()

class TestSecurity:
    """Kompleksowe testy bezpieczeństwa aplikacji"""

    def test_security_headers(self, client: TestClient):
        """Test nagłówków bezpieczeństwa"""
        response = client.get("/api/v1/test")
        headers = response.headers

        # Sprawdź wymagane nagłówki bezpieczeństwa
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
        assert "max-age=31536000" in headers["Strict-Transport-Security"]
        assert headers["X-XSS-Protection"] == "1; mode=block"
        assert "default-src 'self'" in headers["Content-Security-Policy"]
        assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]

    def test_xss_protection(self, client: TestClient):
        """Test ochrony przed atakami XSS"""
        xss_payloads = [
            {"data": "<script>alert('test')</script>"},
            {"data": "javascript:alert('test')"},
            {"data": "<img src=x onerror=alert('test')>"},
            {"form": "<svg onload=alert('test')>"},
            {"nested": {"data": "<script>evil()</script>"}}
        ]

        for payload in xss_payloads:
            response = client.post(
                "/api/v1/test",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 400
            assert "xss attack detected" in response.json()["detail"].lower()

    def test_rate_limiting(self, client: TestClient):
        """Test limitowania liczby żądań"""
        for _ in range(settings.RATE_LIMIT_PER_MINUTE):
            response = client.get("/api/v1/test")
            assert response.status_code == 200

        response = client.get("/api/v1/test")
        assert response.status_code == 429
        assert "too many requests" in response.json()["detail"].lower()

    def test_cors_policy(self, client: TestClient):
        """Test polityki CORS"""
        # Test dla dozwolonego origin
        allowed_origin = "http://localhost:3000"
        headers = {"Origin": allowed_origin}
        response = client.options("/api/v1/test", headers=headers)
        assert response.status_code == 200
        assert response.headers["Access-Control-Allow-Origin"] == allowed_origin
        assert response.headers["Access-Control-Allow-Credentials"] == "true"

        # Test dla niedozwolonego origin
        blocked_origin = "http://evil.com"
        headers = {"Origin": blocked_origin}
        response = client.options("/api/v1/test", headers=headers)
        assert response.status_code == 403

    def test_authentication_flow(self, client: TestClient):
        """Test przepływu uwierzytelniania"""
        register_data = {
            "email": "test@example.com",
            "password": "StrongPass123!",
            "full_name": "Test User"
        }
        register_response = client.post("/api/v1/auth/register", json=register_data)
        assert register_response.status_code == 200

        invalid_login_data = {
            "username": "test@example.com",
            "password": "WrongPass123!"
        }
        for _ in range(5):
            response = client.post("/api/v1/auth/login", data=invalid_login_data)
            assert response.status_code == 401

        response = client.post("/api/v1/auth/login", data=invalid_login_data)
        assert response.status_code == 401
        assert "account is blocked" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_authorization_levels(self, client: TestClient):
        """Test poziomów autoryzacji"""
        user_data = {
            "email": "test@example.com",
            "password": "StrongPass123!",
            "full_name": "Test User"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 200
        
        login_data = {
            "email": user_data["email"],
            "password": user_data["password"]
        }
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        token = response.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/admin/test", headers=headers)
        assert response.status_code == 403
        assert "insufficient permissions" in response.json()["detail"].lower()
        
        response = client.get("/api/v1/premium/test", headers=headers)
        assert response.status_code == 402
        assert "subscription required" in response.json()["detail"].lower()

    def test_session_security(self, client: TestClient):
        """Test bezpieczeństwa sesji"""
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZXhwIjoxNTE2MjM5MDIyfQ.2lNYA2-gNqS0WyR1wHO8AK9AGBqIOVZcwamYDFGmAfM"
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/v1/protected", headers=headers)
        assert response.status_code == 401
        assert "token has expired" in response.json()["detail"].lower()

        invalid_token = "invalid.token.here"
        headers = {"Authorization": f"Bearer {invalid_token}"}
        response = client.get("/api/v1/protected", headers=headers)
        assert response.status_code == 401
        assert "invalid token" in response.json()["detail"].lower()

    def test_sql_injection_protection(self, client: TestClient):
        """Test ochrony przed SQL Injection"""
        injection_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users; --",
            "' OR '1'='1' --",
            "admin' --"
        ]

        for payload in injection_payloads:
            response = client.get(f"/api/v1/users?query={payload}")
            assert response.status_code == 400
            assert "invalid input" in response.json()["detail"].lower()

    def test_file_upload_security(self, client: TestClient):
        """Test bezpieczeństwa uploadu plików"""
        malicious_files = [
            {
                'file': ('evil.php', '<?php system($_GET["cmd"]); ?>', 'application/x-php')
            },
            {
                'file': ('shell.jsp', '<% Runtime.getRuntime().exec(request.getParameter("cmd")); %>', 'application/x-jsp')
            }
        ]

        for file_data in malicious_files:
            files = {
                'file': file_data['file']
            }
            response = client.post("/api/v1/upload", files=files)
            assert response.status_code == 400
            assert "invalid file" in response.json()["detail"].lower() 