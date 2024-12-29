from redis import Redis
from app.core.settings import Settings
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self):
        self.settings = Settings()
        self.redis = Redis.from_url(self.settings.REDIS_URL)
        self.max_requests = 100  # na minutę
        self.window = 60  # sekund
        
    async def is_rate_limited(self, client_ip: str) -> bool:
        key = f"rate_limit:{client_ip}"
        current = self.redis.get(key)
        
        if not current:
            self.redis.setex(key, self.window, 1)
            return False
            
        if int(current) >= self.max_requests:
            return True
            
        self.redis.incr(key)
        return False 