from redis import Redis
from app.config.settings import settings

def get_redis_client(host=None):
    """Tworzy i zwraca klienta Redis z opcjonalną konfiguracją hosta"""
    if host:
        return Redis(host=host, port=settings.REDIS_PORT, db=0)
    return Redis.from_url(settings.REDIS_URL)

redis_client = get_redis_client() 