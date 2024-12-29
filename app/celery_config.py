import os
from celery import Celery
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

# Ustawiamy zmienne środowiskowe dla Celery
os.environ.setdefault('CELERY_BROKER_URL', settings.CELERY_BROKER_URL)
os.environ.setdefault('CELERY_RESULT_BACKEND', settings.CELERY_RESULT_BACKEND)
os.environ.setdefault('SERPAPI_KEY', settings.SERPAPI_KEY)

# Inicjalizacja aplikacji Celery
try:
    celery_app = Celery('seo')
    celery_app.config_from_object(settings)
except AttributeError as e:
    logger.error(f"Błąd konfiguracji Celery: {str(e)}")
    raise

# Konfiguracja podstawowych ustawień
celery_app.conf.update(
    broker_url=settings.CELERY_BROKER_URL,
    result_backend=settings.CELERY_RESULT_BACKEND,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
    worker_max_tasks_per_child=1,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    task_reject_on_worker_lost=True
)

# Dodajemy konfigurację SERPAPI
celery_app.conf.serpapi_key = settings.SERPAPI_KEY

# Importujemy zadania
celery_app.autodiscover_tasks(['app'])

if __name__ == '__main__':
    celery_app.start() 