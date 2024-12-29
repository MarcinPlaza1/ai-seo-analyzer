from typing import Dict, List
import openai
from ..config.settings import settings
from ..utils.text_processors import clean_text

class AIAnalysisService:
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        
    async def analyze_content_structure(self, content: str) -> Dict:
        """Analiza struktury treści i sugestie ulepszeń"""
        prompt = f"""Przeanalizuj poniższą treść pod kątem SEO i struktury:
        {clean_text(content[:3000])}
        
        Zwróć analizę w następującym formacie JSON:
        1. Ocena czytelności (1-10)
        2. Sugestie poprawy struktury
        3. Brakujące elementy
        4. Propozycje nagłówków
        5. Słowa kluczowe do dodania"""
        
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[{"role": "system", "content": "Jesteś ekspertem SEO."},
                     {"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content

    async def generate_meta_improvements(self, current_meta: Dict) -> Dict:
        """Generuje ulepszone wersje meta tagów"""
        prompt = f"""Obecne meta tagi:
        Title: {current_meta.get('title', '')}
        Description: {current_meta.get('description', '')}
        
        Zaproponuj ulepszone wersje, które:
        1. Lepiej wykorzystują słowa kluczowe
        2. Są bardziej przekonujące
        3. Mieszczą się w limitach znaków
        4. Zawierają call-to-action"""
        
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[{"role": "system", "content": "Jesteś ekspertem SEO."},
                     {"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content

    async def analyze_competition_gap(self, main_content: str, competitor_content: str) -> Dict:
        """Analiza luk w treści względem konkurencji"""
        prompt = f"""Porównaj dwie treści i znajdź luki:
        
        Nasza treść:
        {clean_text(main_content[:1500])}
        
        Treść konkurencji:
        {clean_text(competitor_content[:1500])}
        
        Zidentyfikuj:
        1. Brakujące tematy
        2. Różnice w słowach kluczowych
        3. Elementy do dodania
        4. Przewagi konkurencji"""
        
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[{"role": "system", "content": "Jesteś ekspertem SEO i analizy konkurencji."},
                     {"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content 