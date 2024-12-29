from app.models import Audit
from app.core.database import SessionLocal
from typing import Optional

class AuditService:
    def __init__(self):
        self.db = SessionLocal()
    
    async def get_audit(self, audit_id: int) -> Optional[Audit]:
        return await self.db.query(Audit).filter(Audit.id == audit_id).first()
        
    async def create_audit(self, data: dict, owner_id: int) -> Audit:
        audit = Audit(url=data["url"], owner_id=owner_id)
        self.db.add(audit)
        await self.db.commit()
        return audit

audit_service = AuditService() 