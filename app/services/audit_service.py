from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.models import Audit, AuditPage
from app.core.error_handling import AuditNotFound
from app.core.cache_manager import CacheManager
from datetime import datetime
import json
from fastapi import HTTPException

class AuditService:
    def __init__(self, db: Session):
        self.db = db
        self.cache = CacheManager()
    
    async def get_audit(self, audit_id: int) -> Optional[Audit]:
        audit = await self.db.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            raise HTTPException(status_code=404, detail="Audit not found")
        return audit
    
    async def create_audit(self, audit_data: Dict, owner_id: int) -> Audit:
        """Tworzy nowy audit"""
        audit = Audit(
            url=audit_data["url"],
            title=audit_data["title"],
            description=audit_data["description"],
            keywords=json.dumps(audit_data["keywords"]),
            owner_id=owner_id,
            status="pending",
            meta_title=None,
            meta_description=None,
            status_code=None,
            audit_data=None,
            suggestions_data=None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(audit)
        return audit
    
    async def get_user_audits(self, user_id: int) -> List[Audit]:
        """Pobiera wszystkie audyty użytkownika"""
        return self.db.query(Audit).filter(Audit.owner_id == user_id).all()
    
    async def get_audit_status(self, audit_id: int) -> str:
        """Pobiera status auditu"""
        audit = await self.get_audit(audit_id)
        return audit.status
    
    async def analyze_audit(self, audit_id: int, analysis_type: str) -> Dict:
        """Analizuje audit"""
        audit = await self.get_audit(audit_id)
        task = unified_analysis_task.delay(audit_id, analysis_type)
        return {"task_id": task.id, "status": "analysis_started"}
    
    async def generate_report(self, audit_id: int, report_options: Dict) -> None:
        """Generuje raport w tle"""
        audit = await self.get_audit(audit_id)
        # TODO: Implementacja generowania raportu
        pass
    
    async def get_report(self, audit_id: int) -> Dict:
        """Pobiera wygenerowany raport"""
        audit = await self.get_audit(audit_id)
        # TODO: Implementacja pobierania raportu
        return {"report": "not_implemented"}
    
    async def generate_suggestions(self, audit_id: int, suggestion_type: str) -> List[str]:
        """Generuje sugestie dla auditu"""
        audit = await self.get_audit(audit_id)
        # TODO: Implementacja generowania sugestii
        return ["Suggestion 1", "Suggestion 2"] 