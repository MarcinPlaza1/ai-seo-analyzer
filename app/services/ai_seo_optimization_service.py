from typing import Dict, List
import openai
from datetime import datetime
from ..config.settings import settings
from ..utils.text_processors import clean_text
from ..models.audit import Audit

class AISEOOptimizationService:
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY

    async def analyze_content_gaps(self, main_content: str, serp_data: Dict) -> Dict:
        """Analiza luk w treści względem top 10 SERP"""
        prompt = f"""Jako ekspert SEO, przeanalizuj treść strony względem top 10 wyników z SERP:

        Nasza treść:
        {clean_text(main_content[:2000])}

        Top 10 SERP dane:
        {serp_data}

        Zidentyfikuj:
        1. Brakujące tematy i słowa kluczowe
        2. Różnice w strukturze treści
        3. Optymalne długości sekcji
        4. Sugestie rozbudowy treści
        5. Propozycje nowych podtematów"""

        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Jesteś ekspertem SEO i content marketingu."},
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message.content

    async def generate_content_plan(self, audit_data: Dict) -> Dict:
        """Generuje plan rozwoju treści"""
        content_data = {
            'current_content': audit_data.get('text_content', ''),
            'meta_data': audit_data.get('meta_tags', {}),
            'headings': audit_data.get('headings', []),
            'competitors': audit_data.get('competitor_analysis', {})
        }

        prompt = f"""Stwórz kompleksowy plan rozwoju treści na podstawie danych:

        Obecna treść i struktura:
        {content_data}

        Plan powinien zawierać:
        1. Priorytety zmian w treści
        2. Propozycje nowych sekcji
        3. Słowa kluczowe do dodania
        4. Optymalizację struktury
        5. Harmonogram wdrożenia"""

        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Jesteś strategiem content marketingu i SEO."},
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message.content

    async def optimize_internal_linking(self, pages_data: List[Dict]) -> Dict:
        """Optymalizacja struktury linków wewnętrznych"""
        prompt = f"""Przeanalizuj strukturę linków wewnętrznych i zaproponuj optymalizację:

        Dane stron:
        {pages_data}

        Zaproponuj:
        1. Nowe połączenia między stronami
        2. Optymalizację anchor tekstów
        3. Hierarchię linkowania
        4. Poprawę struktury nawigacji
        5. Priorytety implementacji"""

        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Jesteś ekspertem architektury informacji i SEO."},
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message.content 