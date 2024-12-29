from typing import TypedDict, List, Dict, Any
from pydantic import BaseModel
from app.models import Audit
import json

class MetaAnalysis(TypedDict):
    titleMissing: bool
    descMissing: bool

class HeadingsAnalysis(TypedDict):
    noH1: bool
    multipleH1: bool

class ImageStats(TypedDict):
    missingAlt: int

class AuditData(TypedDict):
    metaAnalysis: MetaAnalysis
    headingsAnalysis: HeadingsAnalysis
    imageStats: ImageStats

class SEOScore(BaseModel):
    score: int
    reasons: List[str]

class SEOScoreService:
    @staticmethod
    async def calculate(audit: Audit) -> Dict[str, Any]:
        """Oblicza wynik SEO na podstawie danych audytu"""
        data = {}
        if audit.audit_data:
            data = json.loads(audit.audit_data)
            
        score = 100
        reasons = []
        
        # Meta tagi
        meta_analysis = data.get('metaAnalysis', {})
        if meta_analysis.get('titleMissing'):
            score -= 10
            reasons.append('Brak meta title')
        if meta_analysis.get('descMissing'):
            score -= 10
            reasons.append('Brak meta description')
            
        # Nagłówki
        headings = data.get('headingsAnalysis', {})
        if headings.get('noH1') or headings.get('multipleH1'):
            score -= 10
            reasons.append('Problemy z H1')
            
        # Obrazy
        images = data.get('imageStats', {})
        if images.get('missingAlt', 0) > 0:
            score -= 5
            reasons.append('Brakujące alt w obrazach')
            
        return {
            'score': max(0, score),
            'reasons': reasons
        } 