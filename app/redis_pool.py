from redis import ConnectionPool, Redis
from .config import settings

# Singleton pool
redis_pool = ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    max_connections=50,
    decode_responses=True
)

def get_redis() -> Redis:
    return Redis(connection_pool=redis_pool) 