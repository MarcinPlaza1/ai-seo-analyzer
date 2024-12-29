from typing import Dict, List
import spacy
from collections import Counter
from textblob import TextBlob
from .text_analysis_service import TextAnalysisService
from .serp_analysis_service import SerpAnalysisService

class ContentAnalysisService:
    def __init__(self):
        self.nlp = spacy.load("pl_core_news_sm")
        self.text_service = TextAnalysisService()
        self.serp_service = SerpAnalysisService()

    async def analyze_content_depth(self, text: str, main_keyword: str) -> Dict:
        doc = self.nlp(text)
        blob = TextBlob(text)
        
        # Analiza semantyczna
        semantic_analysis = {
            'keyword_density': self._calculate_keyword_density(doc, main_keyword),
            'topic_clusters': self._identify_topic_clusters(doc),
            'readability_score': blob.sentiment.polarity,
            'subjectivity_score': blob.sentiment.subjectivity,
            'content_structure': self._analyze_content_structure(doc, text)
        }
        
        # Porównanie z konkurencją
        competitors_data = await self.serp_service.analyze_serp_position(main_keyword, limit=5)
        
        return {
            'semantic_analysis': semantic_analysis,
            'competitors_comparison': competitors_data,
            'improvement_suggestions': self._generate_content_suggestions(semantic_analysis, competitors_data)
        }

    def _calculate_keyword_density(self, doc, keyword: str) -> float:
        keyword_tokens = self.nlp(keyword)
        matches = sum(1 for token in doc if any(t.text.lower() == token.text.lower() for t in keyword_tokens))
        return matches / len([t for t in doc if not t.is_punct])

    def _identify_topic_clusters(self, doc) -> List[Dict]:
        noun_phrases = [chunk.text for chunk in doc.noun_chunks]
        return [
            {'phrase': phrase, 'count': count}
            for phrase, count in Counter(noun_phrases).most_common(10)
        ]

    def _analyze_content_structure(self, doc, text: str) -> Dict:
        sentences = list(doc.sents)
        return {
            'avg_sentence_length': sum(len(sent) for sent in sentences) / len(sentences),
            'paragraph_count': text.count('\n\n') + 1,
            'complex_words_ratio': len([t for t in doc if len(t.text) > 6]) / len(doc)
        } 