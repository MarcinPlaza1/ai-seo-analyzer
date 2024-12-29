from typing import TypedDict, List
from app.models import Audit
import json

class Suggestion(TypedDict):
    type: str
    priority: str
    message: str

class SEOSuggestionsService:
    @staticmethod
    async def generate(audit: Audit) -> List[Suggestion]:
        """Generuje sugestie SEO na podstawie danych audytu"""
        data = json.loads(audit.audit_data) if audit.audit_data else {}
        suggestions = []
        
        # Meta tagi
        meta = data.get('metaAnalysis', {})
        if meta.get('titleMissing'):
            suggestions.append({
                'type': 'meta',
                'priority': 'high',
                'message': 'Dodaj meta title'
            })
            
        # Nagłówki
        headings = data.get('headingsAnalysis', {})
        if headings.get('noH1'):
            suggestions.append({
                'type': 'headings',
                'priority': 'high',
                'message': 'Dodaj nagłówek H1'
            })
            
        return suggestions 