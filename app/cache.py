from functools import lru_cache
from typing import Optional
from .models import Audit
from .database_utils import get_db

@lru_cache(maxsize=100)
async def get_cached_audit(audit_id: int) -> Optional[Audit]:
    """Cache dla często odczytywanych audytów"""
    with get_db() as db:
        return db.query(Audit).filter(Audit.id == audit_id).first() 