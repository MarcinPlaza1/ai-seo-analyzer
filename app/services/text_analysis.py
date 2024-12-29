from typing import Dict, List
import re
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from collections import Counter

class TextAnalysisService:
    def __init__(self):
        try:
            self.stop_words = set(stopwords.words('english'))
        except:
            import nltk
            nltk.download('punkt')
            nltk.download('stopwords')
            self.stop_words = set(stopwords.words('english'))

    def analyze_text(self, text: str) -> Dict:
        if not text:
            return {
                "word_count": 0,
                "sentence_count": 0,
                "keyword_density": {},
                "readability_score": 0
            }

        # Podstawowa analiza
        sentences = sent_tokenize(text)
        words = word_tokenize(text.lower())
        words = [word for word in words if word.isalnum() and word not in self.stop_words]

        # Gęstość słów kluczowych
        word_freq = Counter(words)
        total_words = len(words)
        keyword_density = {
            word: count/total_words 
            for word, count in word_freq.most_common(10)
        }

        # Prosty wskaźnik czytelności
        avg_sentence_length = len(words) / len(sentences) if sentences else 0
        readability_score = 100 - (avg_sentence_length * 1.015)

        return {
            "word_count": total_words,
            "sentence_count": len(sentences),
            "keyword_density": keyword_density,
            "readability_score": round(readability_score, 2)
        } 