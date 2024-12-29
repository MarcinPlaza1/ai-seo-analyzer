from typing import Dict, Any
import aiohttp
from bs4 import BeautifulSoup

class ImageAnalysisService:
    @staticmethod
    async def analyze(url: str) -> Dict[str, Any]:
        """Analizuje obrazy na stronie"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                images = soup.find_all('img')
                
                return {
                    'total_images': len(images),
                    'missing_alt': len([img for img in images if not img.get('alt')]),
                    'images': [{'src': img.get('src', ''), 'alt': img.get('alt', '')} for img in images]
                } 