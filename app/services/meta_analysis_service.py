from typing import Dict, Any
import aiohttp
from bs4 import BeautifulSoup

class MetaAnalysisService:
    @staticmethod
    async def analyze(url: str) -> Dict[str, Any]:
        """Analizuje meta tagi na stronie"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                title = soup.find('meta', {'name': 'title'}) or soup.find('title')
                description = soup.find('meta', {'name': 'description'})
                
                return {
                    'title': title.text if title else None,
                    'description': description.get('content') if description else None,
                    'has_title': bool(title),
                    'has_description': bool(description)
                } 