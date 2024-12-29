from typing import Dict, Optional, List
from pydantic import BaseModel, HttpUrl, Field

class AuditInputValidator(BaseModel):
    url: HttpUrl
    max_pages: Optional[int] = 100
    check_external: Optional[bool] = False
    keywords: Optional[List[str]] = []

class AIAnalysisInput(BaseModel):
    content: str = Field(min_length=10, max_length=50000)
    competitor_urls: Optional[List[HttpUrl]] = []
    page_type: Optional[str] = "website" 