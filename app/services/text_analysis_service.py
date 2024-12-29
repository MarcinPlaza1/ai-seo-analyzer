import spacy
import pandas as pd
from typing import List, Dict
import openai
from ..config.settings import settings

nlp = spacy.load("pl_core_news_sm")

class TextAnalysisService:
    @staticmethod
    def analyze_text(text: str) -> Dict:
        doc = nlp(text)
        
        # Podstawowa analiza
        analysis = {
            "sentences_count": len(list(doc.sents)),
            "words_count": len([token for token in doc if not token.is_punct]),
            "key_phrases": [chunk.text for chunk in doc.noun_chunks],
            "named_entities": [(ent.text, ent.label_) for ent in doc.ents]
        }
        
        return analysis

    @staticmethod
    async def get_seo_suggestions(analysis: Dict) -> Dict:
        prompt = f"""
        Przeanalizuj tekst o następującej charakterystyce:
        - Liczba zdań: {analysis['sentences_count']}
        - Liczba słów: {analysis['words_count']}
        - Główne frazy: {', '.join(analysis['key_phrases'][:5])}
        
        Zaproponuj optymalizacje SEO.
        """
        
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Jesteś ekspertem SEO."},
                {"role": "user", "content": prompt}
            ]
        )
        
        return {"suggestions": response.choices[0].message.content} 