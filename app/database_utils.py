from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy.orm import Session
from .core.database import SessionLocal
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from .models import Audit

@contextmanager
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 

async def get_audit_with_pages(db: Session, audit_id: int) -> Optional[Audit]:
    query = (
        select(Audit)
        .options(joinedload(Audit.pages))
        .where(Audit.id == audit_id)
    )
    return (await db.execute(query)).scalar_one_or_none() 