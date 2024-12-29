from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.models.audit import AuditCreate, AuditResponse
from app.services.audit_service import AuditService
from app.core.security import get_current_user
from app.core.permissions import check_permissions
from app.core.database import get_db

router = APIRouter()

@router.post("/create", response_model=AuditResponse)
async def create_audit(
    audit_data: AuditCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    try:
        audit_service = AuditService(db)
        audit = await audit_service.create_audit(audit_data.dict(), current_user.id)
        return AuditResponse(
            id=audit.id,
            url=audit.url,
            status=audit.status,
            meta_title=audit.meta_title,
            meta_description=audit.meta_description,
            status_code=audit.status_code,
            audit_data=audit.audit_data,
            suggestions_data=audit.suggestions_data,
            owner_id=audit.owner_id,
            created_at=audit.created_at,
            updated_at=audit.updated_at
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{audit_id}/status")
async def get_audit_status(
    audit_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    try:
        audit_service = AuditService(db)
        await check_permissions(current_user, audit_id, db)
        status = audit_service.get_audit_status(audit_id)
        return {"status": status}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{audit_id}/analyze/{analysis_type}")
async def analyze_audit(
    audit_id: int,
    analysis_type: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    try:
        audit_service = AuditService(db)
        await check_permissions(current_user, audit_id, db)
        result = audit_service.analyze_audit(audit_id, analysis_type)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{audit_id}/generate_report")
async def generate_report(
    audit_id: int,
    report_options: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    try:
        audit_service = AuditService(db)
        await check_permissions(current_user, audit_id, db)
        background_tasks.add_task(audit_service.generate_report, audit_id, report_options)
        return {"message": "Report generation started"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{audit_id}/download_report")
async def download_report(
    audit_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    try:
        audit_service = AuditService(db)
        await check_permissions(current_user, audit_id, db)
        report = audit_service.get_report(audit_id)
        return report
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{audit_id}/generate_suggestions")
async def generate_suggestions(
    audit_id: int,
    suggestion_type: Dict[str, str],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    try:
        audit_service = AuditService(db)
        await check_permissions(current_user, audit_id, db)
        suggestions = audit_service.generate_suggestions(audit_id, suggestion_type["type"])
        return {"suggestions": suggestions}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
