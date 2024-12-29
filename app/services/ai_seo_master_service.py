from typing import Dict, List
import openai
from datetime import datetime
from ..config.settings import settings
from ..utils.text_processors import clean_text
from ..services.performance_analysis_service import PerformanceAnalysisService
from ..services.ai_technical_seo_service import AITechnicalSEOService
from ..services.ai_seo_optimization_service import AISEOOptimizationService

class AISEOMasterService:
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        self.technical_service = AITechnicalSEOService()
        self.optimization_service = AISEOOptimizationService()
        self.performance_service = PerformanceAnalysisService()

    async def generate_master_analysis(self, audit_data: Dict) -> Dict:
        """Generuje kompleksową analizę i plan działania"""
        
        # Zbierz wszystkie dane
        performance_data = audit_data.get('performance_analysis', {})
        content_data = audit_data.get('content_quality_analysis', {})
        technical_data = audit_data.get('technical_seo_analysis', {})
        
        prompt = f"""Jako główny ekspert SEO, przeanalizuj wszystkie aspekty strony:

        Wydajność:
        {performance_data}

        Treść:
        {content_data}

        Aspekty techniczne:
        {technical_data}

        Przygotuj:
        1. Główne problemy i priorytety
        2. Plan działania na 3 miesiące
        3. Szacowany wpływ na ranking
        4. Budżet i zasoby
        5. KPI i metryki sukcesu"""

        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Jesteś głównym strategiem SEO z 15-letnim doświadczeniem."},
                {"role": "user", "content": prompt}
            ]
        )

        return {
            'master_analysis': response.choices[0].message.content,
            'timestamp': datetime.now().isoformat()
        }

    async def generate_competitive_advantage_plan(self, audit_data: Dict) -> Dict:
        """Generuje plan budowania przewagi konkurencyjnej"""
        competitor_data = audit_data.get('competition_analysis', {})
        serp_data = audit_data.get('serp_analysis', {})

        prompt = f"""Przeanalizuj pozycję konkurencyjną i zaproponuj strategię:

        Dane konkurencji:
        {competitor_data}

        Dane SERP:
        {serp_data}

        Określ:
        1. Unikalne możliwości
        2. Luki rynkowe
        3. Strategię content marketingu
        4. Plan linkbuilding
        5. Innowacyjne podejścia"""

        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Jesteś strategiem marketingu cyfrowego."},
                {"role": "user", "content": prompt}
            ]
        )

        return response.choices[0].message.content 