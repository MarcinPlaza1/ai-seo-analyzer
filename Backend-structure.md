# Backend Structure

• app  
  ┣ api/endpoints  
  ┃ ┣ audit.py – zarządzanie audytami SEO  
  ┃ ┗ auth.py – autentykacja użytkowników  
  
  ┣ services  
  ┃ ┣ seo_score_service.py – obliczanie wyników SEO  
  ┃ ┣ ai_seo_master_service.py – integracja z OpenAI  
  ┃ ┣ audit_service.py – główna logika audytów  
  ┃ ┗ content_analysis_service.py – analiza treści  
  
  ┣ tasks  
  ┃ ┣ analyze_content_quality.py  
  ┃ ┣ analyze_performance.py  
  ┃ ┗ analyze_technical_seo.py  
  
  ┣ core  
  ┃ ┣ activity_monitor.py – monitoring aktywności  
  ┃ ┣ session_manager.py – zarządzanie sesjami  
  ┃ ┗ settings.py – konfiguracja (Redis, Celery, ES)  

  ┣ models  
  ┃ ┣ audit.py – model danych audytu  
  ┃ ┗ user.py – model użytkownika  

• integrations  
  ┣ elasticsearch/ – indeksowanie wyników  
  ┣ openai/ – integracja z GPT  
  ┗ lighthouse/ – analiza wydajności  

• workers  
  ┣ celery.py – konfiguracja workera  
  ┗ tasks/ – zadania asynchroniczne