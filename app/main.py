# app/main.py

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.routers import audit, auth
from app.core.database import Base, engine
from app.middleware.security import SecurityMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.settings import settings
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware

limiter = Limiter(key_func=get_remote_address)

async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )

def create_app() -> FastAPI:
    # Inicjalizacja bazy danych
    Base.metadata.create_all(bind=engine)
    
    app = FastAPI(
        title="SEO MVP",
        version="0.3.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Dodaj obsługę wyjątków
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    @app.get("/")
    async def root():
        return {
            "name": "SEO MVP API",
            "version": "1.0.0"
        }
    
    # Konfiguracja rate limitera
    app.state.limiter = limiter
    
    # Dodaj middleware w odpowiedniej kolejności
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"]
    )
    
    # Dodaj routery - używamy bezpośrednio obiektów router z modułów
    app.include_router(audit)
    app.include_router(auth)
    
    return app

app = create_app()

@app.get("/api/v1/test")
async def test_endpoint():
    """Endpoint testowy dla testów bezpieczeństwa"""
    return {"message": "test endpoint"}

@app.post("/api/v1/test")
async def test_post_endpoint():
    """Endpoint testowy dla testów POST"""
    return {"message": "test post endpoint"}

@app.get("/api/v1/users")
async def test_users_endpoint():
    """Endpoint testowy dla testów SQL injection"""
    return {"message": "users endpoint"}

@app.post("/api/v1/upload")
async def test_upload_endpoint():
    """Endpoint testowy dla testów uploadu plików"""
    return {"message": "upload endpoint"}

@app.get("/api/v1/protected")
async def test_protected_endpoint():
    """Endpoint testowy dla testów autoryzacji"""
    return {"message": "protected endpoint"}
