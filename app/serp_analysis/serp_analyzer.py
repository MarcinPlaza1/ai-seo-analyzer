from serpapi import GoogleSearch
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse
from collections import Counter
import os
from ..config.settings import settings
from ..exceptions import SerpAPIError

class SerpAnalyzer:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('SERPAPI_KEY')
        
    def analyze_keyword(self, keyword: str, domain: str) -> Dict[str, Any]:
        try:
            search = GoogleSearch({
                "q": keyword,
                "api_key": self.api_key,
                "num": 100
            })
            results = search.get_dict()
            
            organic_results = results.get("organic_results", [])
            if not organic_results:
                return self._empty_analysis(keyword)
            
            # Analiza pozycji domeny
            domain_positions = [
                i + 1 for i, result in enumerate(organic_results)
                if domain in result.get('link', '')
            ]
            
            return {
                "keyword": keyword,
                "total_results": len(organic_results),
                "domain_positions": domain_positions,
                "avg_position": sum(domain_positions) / len(domain_positions) if domain_positions else None,
                "best_position": min(domain_positions) if domain_positions else None,
                "competitors": self._analyze_competitors(organic_results, domain)
            }
        except Exception as e:
            raise SerpAPIError(f"SerpAPI error: {str(e)}")
            
    def _analyze_competitors(self, results: List[Dict], domain: str) -> List[Dict]:
        competitor_data = {}
        
        for pos, result in enumerate(results, 1):
            result_domain = urlparse(result.get('link', '')).netloc
            if result_domain and result_domain != domain:
                if result_domain not in competitor_data:
                    competitor_data[result_domain] = {
                        'domain': result_domain,
                        'appearances': 0,
                        'positions': []
                    }
                competitor_data[result_domain]['appearances'] += 1
                competitor_data[result_domain]['positions'].append(pos)
        
        return sorted(
            competitor_data.values(),
            key=lambda x: x['appearances'],
            reverse=True
        )[:5]
        
    def _empty_analysis(self, keyword: str) -> Dict[str, Any]:
        return {
            "keyword": keyword,
            "total_results": 0,
            "domain_positions": [],
            "avg_position": None,
            "best_position": None,
            "competitors": []
        } 