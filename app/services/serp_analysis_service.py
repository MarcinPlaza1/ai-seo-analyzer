from typing import List, Dict
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from collections import Counter
from .text_analysis_service import TextAnalysisService

class SerpAnalysisService:
    async def analyze_serp_position(self, keyword: str, domain: str, top_n: int = 10) -> Dict:
        competitors_data = []
        
        async with aiohttp.ClientSession() as session:
            # Symulacja wyników SERP (w rzeczywistości użylibyśmy API Google)
            competitors = await self._get_top_competitors(session, keyword, top_n)
            
            for comp in competitors:
                text_content = await self._fetch_page_content(session, comp['url'])
                analysis = TextAnalysisService.analyze_text(text_content)
                
                competitors_data.append({
                    'url': comp['url'],
                    'position': comp['position'],
                    'word_count': analysis['words_count'],
                    'key_phrases': analysis['key_phrases'][:5],
                    'readability_score': analysis.get('readability_score', 0)
                })
        
        return {
            'keyword': keyword,
            'competitors': competitors_data,
            'avg_word_count': sum(c['word_count'] for c in competitors_data) / len(competitors_data),
            'common_phrases': self._find_common_phrases([c['key_phrases'] for c in competitors_data])
        }

    async def _get_top_competitors(self, session: aiohttp.ClientSession, keyword: str, limit: int) -> List[Dict]:
        # Tu zaimplementowalibyśmy rzeczywiste pobieranie danych z API Google
        # Na razie zwracamy przykładowe dane
        return [{'url': f'https://example{i}.com', 'position': i} for i in range(1, limit+1)]

    def _find_common_phrases(self, phrases_lists: List[List[str]]) -> List[str]:
        all_phrases = [phrase for sublist in phrases_lists for phrase in sublist]
        return [phrase for phrase, count in Counter(all_phrases).most_common(5)] 