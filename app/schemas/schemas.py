from pydantic import BaseModel, HttpUrl, validator
from typing import Optional, Dict, Any
from datetime import datetime

class AuditCreate(BaseModel):
    url: HttpUrl
    
    @validator('url')
    def validate_url(cls, v):
        if not str(v).startswith(('http://', 'https://')):
            raise ValueError('URL musi zaczynać się od http:// lub https://')
        return str(v)

class AuditOut(BaseModel):
    id: int
    url: str
    status: str
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    status_code: Optional[int] = None
    audit_data: Optional[str] = None
    suggestions_data: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AuditPageOut(BaseModel):
    id: int
    url: str
    status_code: Optional[int] = None
    visited: bool
    page_data: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
