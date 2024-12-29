import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    # Upewnij się, że katalog logs istnieje
    os.makedirs('logs', exist_ok=True)
    
    logging.basicConfig(
        handlers=[
            RotatingFileHandler(
                'logs/app.log',
                maxBytes=10000000,
                backupCount=5
            ),
            logging.StreamHandler()
        ],
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Dodaj logger dla Celery
    celery_logger = logging.getLogger('celery')
    celery_logger.setLevel(logging.INFO) 