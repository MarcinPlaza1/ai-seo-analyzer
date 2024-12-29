from typing import Dict, Any
import aiohttp
from bs4 import BeautifulSoup

class HeadingAnalysisService:
    @staticmethod
    async def analyze(url: str) -> Dict[str, Any]:
        """Analizuje nagłówki na stronie"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                headings = {
                    'h1': [h.text.strip() for h in soup.find_all('h1')],
                    'h2': [h.text.strip() for h in soup.find_all('h2')],
                    'h3': [h.text.strip() for h in soup.find_all('h3')]
                }
                
                return {
                    'headings': headings,
                    'has_h1': bool(headings['h1']),
                    'multiple_h1': len(headings['h1']) > 1
                } 