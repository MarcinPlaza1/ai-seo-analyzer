from typing import Any, Optional
import json
from datetime import datetime, timedelta
from redis import Redis
from ..config.settings import settings

class CacheManager:
    def __init__(self):
        redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
        self.redis = Redis.from_url(redis_url)
        
    async def get_cached(self, key: str) -> Optional[Any]:
        """Pobiera dane z cache"""
        data = self.redis.get(key)
        if data:
            return json.loads(data)
        return None
        
    async def set_cached(self, key: str, value: Any, expire: int = 3600) -> None:
        """Zapisuje dane w cache"""
        self.redis.setex(
            key,
            expire,
            json.dumps(value, ensure_ascii=False)
        )
        
    async def invalidate(self, pattern: str) -> None:
        """Invaliduje cache dla danego wzorca"""
        keys = self.redis.keys(pattern)
        if keys:
            self.redis.delete(*keys) 