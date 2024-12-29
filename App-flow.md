# App Flow

1. Rejestracja i logowanie użytkownika  
   • Standardowy proces uwierzytelniania z wykorzystaniem JWT.
   • Wymagane uprawnienia do konkretnych operacji (np. "create_audit", "read_audit").

2. Tworzenie i inicjalizacja audytu  
   • Użytkownik z uprawnieniem "create_audit" wywołuje endpoint /audit/create z URL-em do analizy.
   • System tworzy nowy rekord audytu ze statusem "pending".
   • Rozpoczyna się asynchroniczne zadanie analizy w tle.

3. Proces analizy SEO  
   a) Analiza techniczna
      • Sprawdzanie Core Web Vitals
      • Analiza wydajności strony
      • Generowanie sugestii Schema.org
   
   b) Analiza treści
      • Badanie jakości contentu względem słów kluczowych
      • Analiza nagłówków i struktury
      • Sprawdzanie meta tagów
   
   c) Analiza wydajności
      • Pomiar metryk wydajnościowych
      • Optymalizacja obrazów
      • Analiza czasu ładowania

4. Generowanie raportu i sugestii AI  
   • Obliczanie końcowego wyniku SEO (SEOScoreService)
   • Generowanie szczegółowych sugestii przez AISEOMasterService
   • Zapisywanie wyników w ElasticSearch do późniejszego wyszukiwania

5. Dostęp do wyników  
   • Właściciel audytu może przeglądać wyniki przez endpoint /audit/{audit_id}
   • Możliwość generowania różnych typów raportów (technical, content, links, images, headings, meta, ai)
   • System monitoruje i loguje wszystkie dostępy do raportów