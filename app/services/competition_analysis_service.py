from typing import List, Dict
import spacy
from collections import Counter
from ..services.text_analysis_service import TextAnalysisService

nlp = spacy.load("pl_core_news_sm")

class CompetitionAnalysisService:
    @staticmethod
    async def analyze_competitors(main_text: str, competitor_texts: List[str]) -> Dict:
        # Analiza głównego tekstu
        main_analysis = TextAnalysisService.analyze_text(main_text)
        main_keywords = set(main_analysis["key_phrases"])
        
        # Analiza konkurencji
        competitors_analysis = []
        for text in competitor_texts:
            comp_analysis = TextAnalysisService.analyze_text(text)
            common_keywords = main_keywords.intersection(set(comp_analysis["key_phrases"]))
            
            competitors_analysis.append({
                "common_keywords": list(common_keywords),
                "unique_keywords": list(set(comp_analysis["key_phrases"]) - main_keywords),
                "readability_score": comp_analysis.get("readability_score"),
                "content_length": comp_analysis.get("words_count")
            })
        
        return {
            "main_site_analysis": main_analysis,
            "competitors_analysis": competitors_analysis,
            "market_gaps": list(main_keywords - set().union(*[set(x["common_keywords"]) for x in competitors_analysis]))
        } 