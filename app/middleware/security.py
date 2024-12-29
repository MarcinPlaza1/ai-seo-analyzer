import re
import json
import logging
from typing import Any, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from app.core.settings import settings
from slowapi import Limiter
from slowapi.util import get_remote_address
import redis
from secrets import token_urlsafe
from app.core.deps import get_current_user
from app.models.user import SubscriptionTier
from app.core.database import get_db

logger = logging.getLogger(__name__)

# Konfiguracja Redis dla rate limitingu
try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1
    )
except Exception as e:
    logger.error(f"Błąd podczas inicjalizacji Redis: {e}")
    redis_client = None

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL
)

class SecurityMiddleware(BaseHTTPMiddleware):
    PUBLIC_ENDPOINTS = ["/", "/docs", "/redoc", "/openapi.json", "/api/v1/auth/login", "/api/v1/auth/register"]
    PREMIUM_ENDPOINTS = ["/api/v1/audits/{audit_id}/analyze"]

    def __init__(self, app):
        super().__init__(app)
        self.xss_patterns = [
            r"<script[^>]*>",
            r"javascript:",
            r"data:",
            r"vbscript:",
            r"on\w+\s*=",
            r"<img[^>]*onerror",
            r"<svg[^>]*onload",
            r"<[^>]*onclick",
            r"<[^>]*onmouseover",
            r"<[^>]*onmouseout",
            r"expression\s*\(",
            r"url\s*\(",
            r"document\.",
            r"window\.",
            r"eval\s*\(",
            r"setTimeout\s*\(",
            r"setInterval\s*\(",
            r"new\s+Function\s*\(",
            r"<iframe[^>]*>",
            r"<embed[^>]*>",
            r"<object[^>]*>",
            r"<form[^>]*>",
            r"<meta[^>]*>",
            r"<link[^>]*>",
            r"<applet[^>]*>"
        ]
        
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            # Obsługa CORS preflight
            if request.method == "OPTIONS":
                response = Response()
                origin = request.headers.get("Origin")
                if origin and origin in settings.ALLOWED_ORIGINS:
                    response.headers.update({
                        "Access-Control-Allow-Origin": origin,
                        "Access-Control-Allow-Credentials": "true",
                        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                        "Access-Control-Allow-Headers": "Authorization, Content-Type"
                    })
                    return response
                return JSONResponse(
                    content={"detail": "Origin not allowed"},
                    status_code=403
                )

            # Rate limiting dla niepublicznych endpointów
            if request.url.path not in self.PUBLIC_ENDPOINTS:
                try:
                    client_ip = request.client.host
                    key = f"rate_limit:{client_ip}"
                    
                    # Próba użycia Redis
                    try:
                        if redis_client:
                            request_count = redis_client.incr(key)
                            redis_client.expire(key, 60)
                    except redis.RedisError as e:
                        logger.error(f"Błąd Redis podczas rate limitingu: {e}")
                        # Fallback do limiter.slowapi
                        request_count = await limiter(request)
                        
                    if request_count > settings.RATE_LIMIT_PER_MINUTE:
                        return JSONResponse(
                            content={"detail": "Too many requests"},
                            status_code=429
                        )
                except Exception as e:
                    logger.error(f"Błąd podczas rate limitingu: {e}")
                    # W przypadku błędu, kontynuuj bez rate limitingu

            # Sprawdź XSS i SQL Injection przed przetworzeniem żądania
            if request.method in ["POST", "PUT", "PATCH"]:
                content_type = request.headers.get("content-type", "").lower()
                logger.debug(f"Content-Type: {content_type}")

                if "application/json" in content_type:
                    try:
                        body = await request.json()
                        if self._check_json_xss(body):
                            logger.warning(f"Wykryto atak XSS w JSON payload: {body}")
                            return JSONResponse(
                                content={"detail": "XSS attack detected in JSON payload"},
                                status_code=400
                            )
                    except json.JSONDecodeError as e:
                        logger.error(f"Błąd dekodowania JSON: {e}")
                        return JSONResponse(
                            content={"detail": "Invalid JSON format"},
                            status_code=400
                        )
                elif "application/x-www-form-urlencoded" in content_type:
                    form = await request.form()
                    if any(self._check_xss(str(value)) for value in form.values()):
                        logger.warning(f"Wykryto atak XSS w form data")
                        return JSONResponse(
                            content={"detail": "XSS attack detected in form data"},
                            status_code=400
                        )
                elif "multipart/form-data" in content_type:
                    form = await request.form()
                    if any(self._check_xss(str(value)) for value in form.values()):
                        logger.warning(f"Wykryto atak XSS w multipart form data")
                        return JSONResponse(
                            content={"detail": "XSS attack detected in form data"},
                            status_code=400
                        )
                else:
                    body = await request.body()
                    if self._check_xss(str(body)):
                        logger.warning(f"Wykryto atak XSS w raw body")
                        return JSONResponse(
                            content={"detail": "XSS attack detected"},
                            status_code=400
                        )

            # Sprawdź SQL Injection w parametrach URL
            query_params = request.query_params
            for param in query_params.values():
                if self._check_sql_injection(param):
                    logger.warning(f"Wykryto próbę SQL Injection w parametrach URL: {param}")
                    return JSONResponse(
                        content={"detail": "Invalid input detected"},
                        status_code=400
                    )

            response = await call_next(request)
            
            # Jeśli odpowiedź jest słownikiem, konwertuj ją na JSONResponse
            if isinstance(response, dict):
                response = JSONResponse(content=response)
            
            # Dodaj nagłówki bezpieczeństwa
            nonce = token_urlsafe(16)
            response.headers.update({
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
                "X-XSS-Protection": "1; mode=block",
                "Content-Security-Policy": self._generate_csp(nonce),
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=()",
                "X-Permitted-Cross-Domain-Policies": "none",
                "Cross-Origin-Embedder-Policy": "require-corp",
                "Cross-Origin-Opener-Policy": "same-origin",
                "Cross-Origin-Resource-Policy": "same-origin"
            })
            
            # Obsługa CORS dla normalnych requestów
            origin = request.headers.get("Origin")
            if origin and origin in settings.ALLOWED_ORIGINS:
                response.headers.update({
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Credentials": "true"
                })
            
            return response
            
        except json.JSONDecodeError as e:
            logger.error(f"Błąd dekodowania JSON: {e}")
            return JSONResponse(
                content={"detail": "Invalid JSON format"},
                status_code=400
            )
        except Exception as e:
            logger.error(f"Nieoczekiwany błąd w middleware: {e}")
            return JSONResponse(
                content={"detail": "Internal server error"},
                status_code=500
            )

    def _check_xss(self, value: str) -> bool:
        """Sprawdź czy wartość zawiera potencjalny atak XSS"""
        return any(bool(re.search(pattern, value, re.IGNORECASE)) for pattern in self.xss_patterns)

    def _check_json_xss(self, data: Any) -> bool:
        """Rekurencyjnie sprawdź XSS w strukturze JSON"""
        if isinstance(data, str):
            return self._check_xss(data)
        elif isinstance(data, dict):
            return any(self._check_json_xss(v) for v in data.values())
        elif isinstance(data, list):
            return any(self._check_json_xss(item) for item in data)
        return False

    def _check_sql_injection(self, value: str) -> bool:
        """Sprawdź czy wartość zawiera potencjalny atak SQL Injection"""
        sql_patterns = [
            r"(\s|^)(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)(\s|$)",
            r"(\s|^)(OR|AND)(\s|$)['\"]\s*[=<>]",
            r"--\s*$",
            r"#\s*$",
            r";\s*$",
            r"\/\*.*\*\/",
            r"xp_cmdshell",
            r"exec\s*\(",
            r"''\s*=\s*'",
            r"1\s*=\s*1",
            r"@\w+",
            r"@@\w+"
        ]
        return any(bool(re.search(pattern, value, re.IGNORECASE)) for pattern in sql_patterns)

    def _generate_csp(self, nonce: str) -> str:
        """Generuj Content Security Policy"""
        return (
            f"default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}'; "
            f"style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "form-action 'self';"
        )