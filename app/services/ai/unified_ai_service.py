from typing import Dict, List
from app.services.base_service import BaseService
from app.core.openai_client import OpenAIClient
from app.core.config import settings

class UnifiedAIService(BaseService):
    def __init__(self):
        super().__init__()
        self.openai = OpenAIClient(settings.OPENAI_API_KEY)
    
    async def analyze(self, audit_id: int, analysis_type: str) -> Dict:
        """Unified method for all AI analysis"""
        try:
            audit = await self.get_audit(audit_id)
            
            analysis_methods = {
                'technical': self._analyze_technical_seo,
                'content': self._analyze_content,
                'optimization': self._analyze_optimization,
                'suggestions': self._generate_suggestions
            }
            
            if analysis_type not in analysis_methods:
                raise ValueError(f"Unknown analysis type: {analysis_type}")
                
            return await analysis_methods[analysis_type](audit)
            
        except Exception as e:
            await self.handle_error(e) 