from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any

class AuditCreate(BaseModel):
    url: HttpUrl
    title: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[str] = None

class AuditResponse(BaseModel):
    id: int
    url: str
    status: str
    owner_id: int
    title: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    status_code: Optional[int] = None
    audit_data: Optional[Dict[str, Any]] = None
    suggestions_data: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True 