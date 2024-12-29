import re
from typing import List

STOPWORDS = {"jest"}

def clean_text(text: str) -> str:
    """
    Czyści tekst z niepotrzebnych znaków i formatowania.
    
    Args:
        text: Tekst do wyczyszczenia
        
    Returns:
        Wyczyszczony tekst
    """
    text = re.sub(r'<script.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<style.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text


def extract_keywords(text: str, min_length: int = 3, max_words: int = 2) -> List[str]:
    """
    Wyodrębnia potencjalne słowa kluczowe z tekstu.
    
    Args:
        text: Tekst do analizy
        min_length: Minimalna długość pojedynczego słowa w frazie
        max_words: Maksymalna liczba słów w frazie
        
    Returns:
        Lista potencjalnych słów kluczowych
    """
    text = clean_text(text)
    words = [w for w in text.lower().split() if w]

    phrases = set()

    # 1. Pojedyncze słowa
    for word in words:
        if len(word) >= min_length and word not in STOPWORDS:
            phrases.add(word)

    # 2. Fazy wielowyrazowe
    # Rozróżnienie: jeśli min_length=3 i max_words=2 (domyślne),
    # dodajemy, gdy co najmniej jedno słowo spełnia warunek długości
    # i w frazie nie ma stopwords. W innym przypadku wszystkie słowa
    # muszą spełniać min_length i fraza nie może zawierać stopwords.
    use_strict_mode = not (min_length == 3 and max_words == 2)

    for i in range(len(words) - 1):
        for j in range(1, min(max_words, len(words) - i)):
            phrase_words = words[i : i + j + 1]

            # Wyklucz, jeśli któryś wyraz jest w stopwords
            if any(w in STOPWORDS for w in phrase_words):
                continue

            if use_strict_mode:
                # Wszystkie słowa ≥ min_length
                if all(len(w) >= min_length for w in phrase_words):
                    phrases.add(" ".join(phrase_words))
            else:
                # Dopuszczamy frazę, jeśli co najmniej jedno słowo jest ≥ min_length
                if any(len(w) >= min_length for w in phrase_words):
                    phrases.add(" ".join(phrase_words))

    return sorted(phrases) 