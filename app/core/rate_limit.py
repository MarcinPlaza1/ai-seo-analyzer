from datetime import datetime, timedelta
from fastapi import HTTPException, status
from app.core.redis_client import redis_client
from app.config import settings

class RateLimiter:
    def __init__(self):
        # Domyślne wartości
        self.window_size = getattr(settings, 'RATE_LIMIT_WINDOW_SIZE', 60)  # 1 minuta
        self.max_requests = getattr(settings, 'RATE_LIMIT_MAX_REQUESTS', 100)  # 100 requestów na minutę
    
    async def check_rate_limit(self, user_id: int) -> None:
        """Sprawdza limit zapytań dla użytkownika"""
        key = f"rate_limit:{user_id}"
        current_time = datetime.utcnow().timestamp()
        window_start = current_time - self.window_size
        
        # Usuń stare zapytania
        redis_client.zremrangebyscore(key, 0, window_start)
        
        # Policz aktualne zapytania
        request_count = redis_client.zcard(key)
        
        if request_count >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        
        # Dodaj nowe zapytanie
        redis_client.zadd(key, {str(current_time): current_time})
        redis_client.expire(key, self.window_size) 