from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from app.core.auth import get_current_user
from app.models.user import User, SubscriptionTier
from app.schemas.audit import AuditCreate, AuditResponse
from app.core.security import SecurityService
from app.core.permissions import require_subscription
from typing import List, Dict, Any, Optional
import json
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session
from app.services.audit_service import AuditService
from app.db.database import get_db

router = APIRouter(prefix="/api/v1/audits", tags=["audit"])
security_service = SecurityService()

class AuditCreateRequest(BaseModel):
    url: HttpUrl
    analysis_type: str
    options: Optional[Dict[str, Any]] = None

    class Config:
        json_encoders = {
            HttpUrl: str
        }

@router.get("", response_model=List[AuditResponse])
async def list_audits(current_user: User = Depends(get_current_user)):
    """Lista audytów użytkownika"""
    return []

@router.post("", response_model=AuditResponse)
@require_subscription(SubscriptionTier.PREMIUM)
async def create_audit(
    audit: AuditCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    audit_service = AuditService(db)
    return await audit_service.create_audit(audit, current_user.id)

@router.post("/{audit_id}/analyze")
@require_subscription(SubscriptionTier.PREMIUM)
async def analyze_audit(
    audit_id: int,
    current_user: User = Depends(get_current_user)
):
    """Endpoint do analizy audytu"""
    # Tutaj dodaj logikę analizy audytu
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "success", "message": "Analiza rozpoczęta"}
    ) 