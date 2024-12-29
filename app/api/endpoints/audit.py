from typing import List, Dict, Any
from fastapi import APIRouter, Query, BackgroundTasks, Path, HTTPException, status, Depends, Request
from fastapi.responses import JSONResponse
from celery.result import AsyncResult
from app.models.audit import AuditResponse, AuditCreate
from app.api.deps import User, get_current_user, get_current_user_with_permissions
from app.services.audit_service import AuditService
from app.core.activity_monitor import ActivityMonitor
from app.tasks import unified_analysis_task, generate_ai_suggestions
from app.core.database import get_db
from sqlalchemy.orm import Session
from app.core.permissions import require_role, require_subscription
from app.models.user import UserRole, SubscriptionTier

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])
activity_monitor = ActivityMonitor()

@router.get("/list")
async def list_audits(
    current_user: User = Depends(get_current_user_with_permissions(["read_audit"])),
    db: Session = Depends(get_db)
):
    """Endpoint listowania audytów"""
    audit_service = AuditService(db)
    return await audit_service.list_audits(current_user.id)

@router.post("/create")
@require_role(UserRole.USER)
async def create_audit(
    data: AuditCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Podstawowa funkcjonalność audytu dostępna dla wszystkich użytkowników"""
    audit_service = AuditService(db)
    return await audit_service.create_basic_audit(data, current_user.id)

@router.get("/{audit_id}")
async def get_audit(
    request: Request,
    audit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permissions(required_permissions=["read_audit"]))
):
    """Zabezpieczony endpoint pobierania audytu"""
    audit_service = AuditService(db)
    audit = await audit_service.get_audit(audit_id)
    if audit.owner_id != current_user.id:
        await activity_monitor.log_activity(
            current_user.id,
            "unauthorized_audit_access",
            {"audit_id": audit_id}
        )
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return audit

@router.post("/{audit_id}/analyze/{analysis_type}")
async def analyze_audit(
    request: Request,
    audit_id: int,
    analysis_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permissions(required_permissions=["analyze_audit"]))
):
    """Endpoint chroniony autoryzacją i rate limitingiem"""
    audit_service = AuditService(db)
    audit = await audit_service.get_audit(audit_id)
    if audit.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this audit"
        )
    
    valid_types = ['technical', 'content', 'links', 'images', 'headings', 'meta', 'ai']
    if analysis_type not in valid_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid analysis type. Must be one of: {valid_types}"
        )
    
    task = unified_analysis_task.delay(audit_id, analysis_type)
    return {"task_id": task.id, "analysis_type": analysis_type}

@router.post("/{audit_id}/suggest", response_model=AuditResponse)
async def generate_suggestions(
    request: Request,
    audit_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_permissions(required_permissions=["analyze_audit"])),
    elements: List[str] = Query(None)
):
    """Unified endpoint for generating AI suggestions"""
    audit_service = AuditService(db)
    audit = await audit_service.get_audit(audit_id)
    if audit.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this audit"
        )
        
    background_tasks.add_task(generate_ai_suggestions.delay, audit_id, elements)
    return {"message": "Suggestion generation started", "audit_id": audit_id} 

@router.post("/analyze/{audit_id}/ai")
@require_role(UserRole.USER)
@require_subscription(SubscriptionTier.PREMIUM)
async def analyze_with_ai(
    audit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Funkcjonalność premium - analiza AI"""
    audit_service = AuditService(db)
    return await audit_service.analyze_with_ai(audit_id, current_user.id) 