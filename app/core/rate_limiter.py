from typing import Dict, Optional
import asyncio
from datetime import datetime, timedelta
from redis import Redis
from ..config.settings import settings

class RateLimiter:
    def __init__(self):
        redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
        self.redis = Redis.from_url(redis_url)
        self.default_limit = settings.DEFAULT_RATE_LIMIT
        
    async def check_limit(self, key: str, limit: Optional[int] = None) -> bool:
        """Sprawdza czy nie przekroczono limitu requestów"""
        current = self.redis.get(key)
        if not current:
            self.redis.setex(key, settings.RATE_LIMIT_WINDOW, 1)
            return True
            
        if int(current) >= (limit or self.default_limit):
            return False
            
        self.redis.incr(key)
        return True

    async def wait_for_slot(self, key: str, limit: Optional[int] = None) -> None:
        """Czeka na dostępny slot w rate limicie"""
        while not await self.check_limit(key, limit):
            await asyncio.sleep(1) 