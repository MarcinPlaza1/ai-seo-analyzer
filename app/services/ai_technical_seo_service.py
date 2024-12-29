from typing import Dict, List
import openai
from ..config.settings import settings
from ..utils.html_parser import HTMLParser

class AITechnicalSEOService:
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        self.html_parser = HTMLParser()

    async def analyze_technical_issues(self, html_content: str, performance_data: Dict) -> Dict:
        """Analiza technicznych aspektów SEO z wykorzystaniem GPT-4"""
        technical_data = self.html_parser.extract_technical_data(html_content)
        
        prompt = f"""Jako ekspert SEO, przeanalizuj dane techniczne strony:

        Dane wydajnościowe:
        {performance_data}

        Dane techniczne:
        {technical_data}

        Przeanalizuj i zwróć:
        1. Krytyczne problemy techniczne
        2. Sugestie optymalizacji
        3. Priorytety napraw
        4. Wpływ na SEO
        5. Szacowany czas naprawy"""

        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Jesteś ekspertem technical SEO z 10-letnim doświadczeniem."},
                {"role": "user", "content": prompt}
            ]
        )
        
        return {
            'analysis': response.choices[0].message.content,
            'technical_data': technical_data
        }

    async def generate_schema_suggestions(self, content: str, page_type: str) -> Dict:
        """Generuje sugestie Schema.org markup"""
        prompt = f"""Analizując treść strony typu {page_type}:

        {content[:2000]}

        Zaproponuj odpowiedni Schema.org markup, który:
        1. Najlepiej opisze zawartość
        2. Zwiększy widoczność w SERP
        3. Będzie zgodny z wytycznymi Google
        
        Zwróć JSON-LD oraz wyjaśnienie wybranych właściwości."""

        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Jesteś ekspertem Schema.org i strukturalnych danych."},
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message.content

    async def analyze_core_web_vitals(self, performance_metrics: Dict) -> Dict:
        """Analiza Core Web Vitals i sugestie poprawy"""
        prompt = f"""Przeanalizuj metryki Core Web Vitals:

        {performance_metrics}

        Określ:
        1. Główne problemy wpływające na wyniki
        2. Konkretne rozwiązania techniczne
        3. Priorytety optymalizacji
        4. Szacowany wpływ na ranking
        5. Plan wdrożenia poprawek"""

        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Jesteś ekspertem Core Web Vitals i wydajności stron."},
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message.content 