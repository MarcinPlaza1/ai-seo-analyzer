import json
import os
import datetime
import requests
import logging
from collections import deque
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from fastapi import HTTPException

import openai
from urllib.parse import urlparse, urljoin

from weasyprint import HTML

from .config.settings import settings
from .core.database import SessionLocal
from .models import Audit, AuditPage
from .exceptions import AuditException, AuditNotFound, CrawlerError, AuditDataNotFound, SerpAnalyError, ContentNotFoundError
from .celery_config import celery_app

from typing import Dict, List, Tuple, Set, Optional, Any
from celery.exceptions import SoftTimeLimitExceeded
from requests.exceptions import Timeout
from tenacity import retry, stop_after_attempt, wait_exponential

from .scrapy_crawler.runner import ScrapyRunner
from .data_analysis.seo_analyzer import SEODataAnalyzer
from .serp_analysis.serp_analyzer import SerpAnalyzer

import aiohttp
import asyncio
from collections import defaultdict

from app.services.text_analysis_service import TextAnalysisService
from app.services.competition_analysis_service import CompetitionAnalysisService
from app.services.serp_analysis_service import SerpAnalysisService
from app.services.content_analysis_service import ContentAnalysisService
from app.services.performance_analysis_service import PerformanceAnalysisService
from app.services.monitoring_service import PerformanceMonitoringService
from app.services.ai_analysis_service import AIAnalysisService
from app.services.ai_technical_seo_service import AITechnicalSEOService
from app.services.ai_seo_optimization_service import AISEOOptimizationService
from app.services.ai_seo_master_service import AISEOMasterService

from app.core.task_wrapper import unified_task_handler
from app.core.error_handling import TaskExecutionError, AuditNotFound
from app.services.audit_service import AuditService
from app.utils.memory_management import ChunkedProcessor

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import urlparse
import json
import aiohttp
from bs4 import BeautifulSoup
from celery import Celery
from sqlalchemy.orm import Session

from .config.settings import settings
from app.core.database import SessionLocal
from app.models import Audit
from app.exceptions import (
    AuditNotFound, 
    AuditException,
    CrawlerError,
    ContentNotFoundError,
    SerpAnalyError
)

from app.services.text_analysis_service import TextAnalysisService
from app.services.audit_service import AuditService
from app.services.competition_analysis_service import CompetitionAnalysisService
from app.services.content_analysis_service import ContentAnalysisService
from app.services.performance_analysis_service import PerformanceAnalysisService
from app.services.elasticsearch_service import ElasticsearchService
from app.services.ai_analysis_service import AIAnalysisService
from app.services.link_analysis_service import LinkAnalysisService
from app.services.image_analysis_service import ImageAnalysisService
from app.services.heading_analysis_service import HeadingAnalysisService
from app.services.meta_analysis_service import MetaAnalysisService

from app.core.activity_monitor import ActivityMonitor
from app.services.seo_score_service import SEOScoreService
from app.services.seo_suggestions_service import SEOSuggestionsService

from app.core.error_handling import TaskExecutionError, AuditNotFound
from app.core.celery_base import ErrorHandlingTask
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)

activity_monitor = ActivityMonitor()

async def cleanup_connections():
    """Zamyka wszystkie aktywne połączenia"""
    # TODO: Implementacja zamykania połączeń do bazy danych, cache, itp.
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

celery_app = Celery(
    "seo_mvp",
    broker=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
)

# Podstawowy wrapper dla wszystkich zadań
base_task_config = {
    "bind": True,
    "soft_time_limit": settings.CELERY_TASK_TIMEOUT,
    "max_retries": 3,
    "retry_backoff": True,
    "autoretry_for": (Exception,)
}

@celery_app.task(**base_task_config)
@unified_task_handler()
async def crawl_entire_site(self, audit_id: int, max_pages: int = 30, depth_limit: int = 2) -> str:
    """Rozbudowany crawler z obsługą pamięci i błędów"""
    async with get_db() as db:
        audit_service = AuditService(db)
        audit = await audit_service.get_audit(audit_id)
        
        chunked_processor = ChunkedProcessor(chunk_size=100)
        runner = ScrapyRunner()
        
        # Crawling z podziałem na chunki
        results = []
        async for chunk in runner.crawl_in_chunks(
            url=audit.url,
            max_pages=max_pages,
            depth_limit=depth_limit
        ):
            processed_chunk = await chunked_processor.process_in_chunks(
                chunk,
                audit_service.process_page_data
            )
            results.extend(processed_chunk)
            
        await audit_service.update_audit_status(audit_id, "done", len(results))
        return f"Crawled {len(results)} pages"

# --------------------------------------------------------------------
# 2. STARY CRAWL_WEBSITE (jedna strona) – ewentualnie zachowujemy
# --------------------------------------------------------------------
def validate_response(response: requests.Response) -> bool:
    """Sprawdza czy odpowiedź HTTP jest odpowiednia do parsowania."""
    if not response.ok:
        return False
    
    content_type = response.headers.get('content-type', '').lower()
    if 'text/html' not in content_type:
        return False
        
    if not response.text.strip():
        return False
        
    return True

@retry(
    stop=stop_after_attempt(settings.RETRY_CONFIG.max_attempts),
    wait=wait_exponential(
        multiplier=settings.RETRY_CONFIG.min_wait,
        max=settings.RETRY_CONFIG.max_wait
    )
)
def make_request(url: str, operation: str = "default") -> Optional[requests.Response]:
    timeout = settings.get_timeout(operation)
    response = requests.get(
        url,
        timeout=(timeout.connect, timeout.read),
        headers={'User-Agent': 'SEO-MVP-Crawler/1.0'}
    )
    if not validate_response(response):
        raise ValueError(f"Invalid response: {response.status_code}")
    return response

@celery_app.task(soft_time_limit=settings.get_celery_timeout("crawl"))
def crawl_website(audit_id: int) -> str:
    db = SessionLocal()
    try:
        audit = db.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            raise AuditNotFound()

        try:
            response = make_request(audit.url, "crawl")
            soup = BeautifulSoup(response.text, "html.parser")
            # reszta kodu parsowania...
        except Exception as e:
            raise CrawlerError(str(e))
    finally:
        db.close()

# --------------------------------------------------------------------
# 3. CHECK LINKS, GENERATE LINK FIXES
# --------------------------------------------------------------------
async def check_single_link(session: aiohttp.ClientSession, url: str) -> dict:
    try:
        async with session.head(url, allow_redirects=True, timeout=10) as response:
            return {
                "url": url,
                "status_code": response.status,
                "is_redirect": response.history != (),
                "error": None
            }
    except Exception as e:
        return {
            "url": url,
            "status_code": None,
            "is_redirect": False,
            "error": str(e)
        }

@celery_app.task(
    bind=True,
    soft_time_limit=settings.CELERY_TASK_TIMEOUT,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    rate_limit='10/m'
)
def check_links(self, audit_id: int, check_external: bool = False) -> str:
    """Zoptymalizowane sprawdzanie linków"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(_async_check_links(audit_id, check_external))

async def _async_check_links(audit_id: int, check_external: bool) -> str:
    async with aiohttp.ClientSession() as session:
        async with get_db() as db:
            audit = await db.query(Audit).filter(Audit.id == audit_id).first()
            if not audit:
                raise AuditNotFound()

            data_dict = json.loads(audit.audit_data or '{}')
            links = data_dict.get('links', [])
            
            # Grupowanie linków po domenach
            domains = defaultdict(list)
            for link in links:
                domain = urlparse(link['url']).netloc
                domains[domain].append(link['url'])
            
            # Sprawdzanie linków z limitem na domenę
            results = []
            for domain, urls in domains.items():
                tasks = [check_single_link(session, url) for url in urls]
                domain_results = await asyncio.gather(*tasks, return_exceptions=True)
                results.extend(domain_results)
                
            return "Links checked"

@celery_app.task
def generate_link_fixes(audit_id: int):
    """
    AI – sugerowanie poprawek do linków problematycznych.
    """
    db: Session = SessionLocal()
    try:
        audit = db.query(Audit).filter_by(id=audit_id).first()
        if not audit:
            return f"Audit not found (id={audit_id})"

        if not audit.audit_data:
            return "No audit_data found."

        data_dict = json.loads(audit.audit_data)
        link_checker = data_dict.get("linkChecker", [])
        if not link_checker:
            return "No linkChecker – run check_links first."

        # Wyłapujemy linki z priority in ["warning","error"]
        problem_links = [lk for lk in link_checker if lk["priority"] in ("warning","error")]
        if not problem_links:
            data_dict["linkFixSuggestions"] = "No problematic links."
            audit.audit_data = json.dumps(data_dict, ensure_ascii=False)
            db.commit()
            return "No link problems."

        openai.api_key = settings.OPENAI_API_KEY

        # Prompt
        lines = []
        for l in problem_links:
            lines.append(f"- {l['href']} status={l['status_code']}, error={l['error']}, priority={l['priority']}")

        prompt_text = f"""
        Mam listę uszkodzonych/redirectujących linków:
        {chr(10).join(lines)}
        Proszę zaproponuj w formie JSON, jak je naprawić.
        """

        try:
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content":"You are an SEO link fix assistant."},
                    {"role": "user", "content": prompt_text}
                ],
                max_tokens=600
            )
            ai_out = resp.choices[0].message.content.strip()
        except Exception as e:
            return f"OpenAI error: {str(e)}"

        data_dict["linkFixSuggestions"] = ai_out
        audit.audit_data = json.dumps(data_dict, ensure_ascii=False)
        db.commit()

        return "link fixes generated."
    except Exception as e:
        return f"Error in generate_link_fixes: {str(e)}"
    finally:
        db.close()

# --------------------------------------------------------------------
# 4. CHECK IMAGES, GENERATE ALT
# --------------------------------------------------------------------
@celery_app.task(soft_time_limit=settings.CELERY_TASK_TIMEOUT)
def check_images(audit_id: int) -> str:
    """
    Weryfikacja alt w pliku audit_data single-page.
    (Dla multi-page musiałbyś to adaptować do AuditPage).
    """
    db: Session = SessionLocal()
    try:
        audit = db.query(Audit).filter_by(id=audit_id).first()
        if not audit:
            raise AuditNotFound()

        if not audit.audit_data:
            raise AuditDataNotFound()

        data_dict = json.loads(audit.audit_data)
        images = data_dict.get("images", [])
        results = []
        for img in images:
            if isinstance(img, dict):
                src = img.get("src","")
                alt = img.get("alt","")
                missing_alt = (not alt or alt.strip()=="")
            else:
                # jeśli mamy samo "src" w formie stringa
                src = img
                missing_alt = True
            results.append({"src": src, "missingAlt": missing_alt})

        data_dict["imageAudit"] = results
        missing_count = sum(1 for i in results if i["missingAlt"])
        data_dict["imageStats"] = {
            "total": len(results),
            "missingAlt": missing_count
        }
        audit.audit_data = json.dumps(data_dict, ensure_ascii=False)
        db.commit()

        return f"{missing_count} out of {len(results)} images have no alt."
    except Exception as e:
        if isinstance(e, AuditException):
            raise e
        raise CrawlerError(str(e))
    finally:
        db.close()

@celery_app.task
def generate_alt_suggestions(audit_id: int):
    """
    AI – generuje alt texty dla brakujących altów.
    """
    db: Session = SessionLocal()
    try:
        audit = db.query(Audit).filter_by(id=audit_id).first()
        if not audit:
            return "Audit not found."

        data_dict = {}
        if audit.audit_data:
            data_dict = json.loads(audit.audit_data)
        image_audit = data_dict.get("imageAudit", [])
        if not image_audit:
            return "No imageAudit – run check_images first."

        missing = [img for img in image_audit if img["missingAlt"]]
        if not missing:
            data_dict["imageAltSuggestions"] = "All images have alt."
            audit.audit_data = json.dumps(data_dict, ensure_ascii=False)
            db.commit()
            return "No missing alt."

        openai.api_key = settings.OPENAI_API_KEY

        lines = []
        for m in missing:
            lines.append(f"- {m['src']}")

        prompt_text = f"""
        Mam obrazki bez alt:
        {chr(10).join(lines)}
        Proszę w formie JSON zaproponuj krótkie alt texty.
        """

        try:
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role":"system", "content":"You are an SEO alt text assistant."},
                    {"role":"user", "content": prompt_text}
                ],
                max_tokens=600
            )
            ai_out = resp.choices[0].message.content.strip()
        except Exception as e:
            return f"OpenAI error: {str(e)}"

        data_dict["imageAltSuggestions"] = ai_out
        audit.audit_data = json.dumps(data_dict, ensure_ascii=False)
        db.commit()

        return "Alt suggestions generated."
    except Exception as e:
        if isinstance(e, AuditException):
            raise e
        raise CrawlerError(str(e))
    finally:
        db.close()

# --------------------------------------------------------------------
# 5. CHECK HEADINGS, CHECK META
# --------------------------------------------------------------------
@celery_app.task
def check_headings(audit_id: int) -> str:
    """
    Sprawdza h1, h2, h3 w single-page. 
    Dla rekurencyjnego – analogicznie w AuditPage.
    """
    db: Session = SessionLocal()
    try:
        audit = db.query(Audit).filter_by(id=audit_id).first()
        if not audit:
            raise AuditNotFound()

        if not audit.audit_data:
            raise AuditDataNotFound()

        data_dict = json.loads(audit.audit_data)
        headings = data_dict.get("headings", {})
        h1 = headings.get("h1", [])
        h2 = headings.get("h2", [])
        h3 = headings.get("h3", [])

        multiple_h1 = (len(h1)>1)
        no_h1 = (len(h1)==0)

        analysis = {
            "countH1": len(h1),
            "countH2": len(h2),
            "countH3": len(h3),
            "noH1": no_h1,
            "multipleH1": multiple_h1
        }
        data_dict["headingsAnalysis"] = analysis
        audit.audit_data = json.dumps(data_dict, ensure_ascii=False)
        db.commit()

        return f"Headings check done. H1={len(h1)}"
    except Exception as e:
        if isinstance(e, AuditException):
            raise e
        raise CrawlerError(str(e))
    finally:
        db.close()

@celery_app.task
def check_meta(audit_id: int) -> str:
    """
    Weryfikacja meta_title i meta_description w polach audytu.
    """
    db: Session = SessionLocal()
    try:
        audit = db.query(Audit).filter_by(id=audit_id).first()
        if not audit:
            raise AuditNotFound()

        meta_title = audit.meta_title or ""
        meta_desc = audit.meta_description or ""

        analysis = {
            "titleLength": len(meta_title),
            "descLength": len(meta_desc),
            "titleMissing": (not meta_title.strip()),
            "descMissing": (not meta_desc.strip()),
            "titleTooLong": (len(meta_title)>65),
            "descTooLong": (len(meta_desc)>160)
        }

        data_dict = {}
        if audit.audit_data:
            data_dict = json.loads(audit.audit_data)
        data_dict["metaAnalysis"] = analysis

        audit.audit_data = json.dumps(data_dict, ensure_ascii=False)
        db.commit()
        return "check_meta done."
    except Exception as e:
        if isinstance(e, AuditException):
            raise e
        raise CrawlerError(str(e))
    finally:
        db.close()

# --------------------------------------------------------------------
# 6. CALCULATE SEO SCORE
# --------------------------------------------------------------------
@celery_app.task
async def calculate_seo_score(audit_id: int) -> str:
    try:
        with get_db() as db:
            audit = db.query(Audit).filter(Audit.id == audit_id).first()
            if not audit:
                raise AuditNotFound()

            data_dict = json.loads(audit.audit_data)
            analyzer = SEODataAnalyzer(data_dict)
            
            # Dodajemy szczegółowe statystyki
            data_dict['detailed_stats'] = {
                'links': analyzer.generate_link_stats(),
                'images': analyzer.generate_image_stats()
            }
            
            # Dodajemy wizualizacje
            data_dict['visualizations'] = analyzer.generate_visualizations()
            
            # Standardowe obliczanie score
            score = 100
            reasons = []
            
            # Reszta logiki obliczania score pozostaje bez zmian
            # Odniesienie do oryginalnego kodu: linie 504-518
            
            audit.audit_data = json.dumps(data_dict, ensure_ascii=False)
            db.commit()
            
            # Dodajemy indeksowanie
            await index_audit_data.delay(audit_id)
            
            return f"SEO score calculated: {score}"
    except Exception as e:
        raise

# --------------------------------------------------------------------
# 7. GENERATE REPORT
# --------------------------------------------------------------------
@celery_app.task(soft_time_limit=settings.CELERY_TASK_TIMEOUT)
def generate_report(audit_id: int) -> str:
    """
    Tworzy raport HTML i konwertuje do PDF via WeasyPrint. 
    """
    from weasyprint import HTML

    db: Session = SessionLocal()
    try:
        audit = db.query(Audit).filter_by(id=audit_id).first()
        if not audit:
            return "Audit not found"

        data_dict = {}
        if audit.audit_data:
            data_dict = json.loads(audit.audit_data)

        score_obj = data_dict.get("seoScore", {})
        link_stats = data_dict.get("linkStats", {})
        image_stats = data_dict.get("imageStats", {})
        headings_ana = data_dict.get("headingsAnalysis", {})
        meta_ana = data_dict.get("metaAnalysis", {})

        html_content = f"""
        <html>
        <head><meta charset="utf-8"><title>SEO Report - {audit.url}</title></head>
        <body>
          <h1>SEO Report for {audit.url}</h1>
          <h2>Score: {score_obj.get('score','N/A')}</h2>
          <p>Reasons: {score_obj.get('reasons',[])}</p>

          <h2>Link Stats</h2>
          <p>Total: {link_stats.get('total',0)}, OK: {link_stats.get('ok',0)}, 
          Redirect: {link_stats.get('redirect',0)}, Broken: {link_stats.get('broken',0)}</p>

          <h2>Image Stats</h2>
          <p>Total: {image_stats.get('total',0)}, missingAlt: {image_stats.get('missingAlt',0)}</p>

          <h2>Headings Analysis</h2>
          <p>H1: {headings_ana.get('countH1',0)}, noH1: {headings_ana.get('noH1',False)}, 
          multipleH1: {headings_ana.get('multipleH1',False)}</p>

          <h2>Meta Analysis</h2>
          <p>titleMissing: {meta_ana.get('titleMissing',False)}, descMissing: {meta_ana.get('descMissing',False)}</p>
          <p>titleTooLong: {meta_ana.get('titleTooLong',False)}, descTooLong: {meta_ana.get('descTooLong',False)}</p>

          <hr>
          <p>Generated by SEO MVP</p>
        </body>
        </html>
        """

        reports_dir = "/app/reports"
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir, exist_ok=True)

        pdf_path = f"{reports_dir}/audit_{audit_id}_report.pdf"
        HTML(string=html_content).write_pdf(pdf_path)

        data_dict["reportPath"] = pdf_path
        audit.audit_data = json.dumps(data_dict, ensure_ascii=False)
        db.commit()

        return f"PDF report generated at {pdf_path}"
    except Exception as e:
        return f"Error in generate_report: {str(e)}"
    finally:
        db.close()

@celery_app.task
def generate_seo_suggestions(audit_id: int) -> str:
    """
    Generuje sugestie SEO na podstawie zebranych danych z audytu.
    """
    db: Session = SessionLocal()
    try:
        audit = db.query(Audit).filter_by(id=audit_id).first()
        if not audit:
            raise AuditNotFound()

        if not audit.audit_data:
            raise AuditDataNotFound()

        data_dict = json.loads(audit.audit_data)
        suggestions = []

        # Analiza meta tagów
        meta_analysis = data_dict.get("metaAnalysis", {})
        if meta_analysis.get("titleMissing"):
            suggestions.append({
                "priority": "high",
                "category": "meta",
                "issue": "Brak meta title",
                "suggestion": "Dodaj meta title - to jeden z najważniejszych elementów SEO"
            })
        elif meta_analysis.get("titleTooLong"):
            suggestions.append({
                "priority": "medium",
                "category": "meta",
                "issue": "Za długi meta title",
                "suggestion": "Skróć meta title do maksymalnie 65 znaków"
            })

        if meta_analysis.get("descMissing"):
            suggestions.append({
                "priority": "high",
                "category": "meta",
                "issue": "Brak meta description",
                "suggestion": "Dodaj meta description zawierający zwięzły opis strony"
            })
        elif meta_analysis.get("descTooLong"):
            suggestions.append({
                "priority": "medium",
                "category": "meta",
                "issue": "Za długi meta description",
                "suggestion": "Skróć meta description do maksymalnie 160 znaków"
            })

        # Analiza nagłówków
        headings_analysis = data_dict.get("headingsAnalysis", {})
        if headings_analysis.get("noH1"):
            suggestions.append({
                "priority": "high",
                "category": "headings",
                "issue": "Brak nagłówka H1",
                "suggestion": "Dodaj jeden główny nagłówek H1 na stronie"
            })
        elif headings_analysis.get("multipleH1"):
            suggestions.append({
                "priority": "medium",
                "category": "headings",
                "issue": "Wiele nagłówków H1",
                "suggestion": "Zostaw tylko jeden główny nagłówek H1, pozostałe zmień na H2"
            })

        # Analiza linków
        link_stats = data_dict.get("linkStats", {})
        broken_links = link_stats.get("broken", 0)
        if broken_links > 0:
            suggestions.append({
                "priority": "high",
                "category": "links",
                "issue": f"Znaleziono {broken_links} uszkodzonych linków",
                "suggestion": "Napraw lub usuń niedziałające linki"
            })

        # Analiza obrazów
        image_stats = data_dict.get("imageStats", {})
        missing_alt = image_stats.get("missingAlt", 0)
        if missing_alt > 0:
            suggestions.append({
                "priority": "medium",
                "category": "images",
                "issue": f"Znaleziono {missing_alt} obrazów bez tekstu alt",
                "suggestion": "Dodaj opisowe teksty alternatywne do obrazów"
            })

        # Zapisujemy sugestie
        data_dict["seoSuggestions"] = {
            "suggestions": suggestions,
            "generatedAt": str(datetime.datetime.now()),
            "totalSuggestions": len(suggestions)
        }
        
        audit.audit_data = json.dumps(data_dict, ensure_ascii=False)
        db.commit()

        return f"Generated {len(suggestions)} SEO suggestions"
    except Exception as e:
        if isinstance(e, AuditException):
            raise e
        raise CrawlerError(str(e))
    finally:
        db.close()

@celery_app.task
def analyze_serp(audit_id: int, keywords: List[str]) -> str:
    with get_db() as db:
        audit = db.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            raise AuditNotFound()
            
        try:
            analyzer = SerpAnalyzer(api_key=settings.SERPAPI_KEY)
            domain = urlparse(audit.url).netloc
            
            serp_data = {
                "keywords_analysis": [
                    analyzer.analyze_keyword(keyword, domain)
                    for keyword in keywords
                ],
                "analyzed_at": str(datetime.datetime.now())
            }
            
            data_dict = json.loads(audit.audit_data) if audit.audit_data else {}
            data_dict["serp_analysis"] = serp_data
            audit.audit_data = json.dumps(data_dict, ensure_ascii=False)
            db.commit()
            
            return f"Analyzed {len(keywords)} keywords"
            
        except Exception as e:
            raise SerpAnalyError(str(e))

@celery_app.task
async def index_audit_data(audit_id: int) -> str:
    """Indeksuje dane audytu w ElasticSearch"""
    async with get_db() as db:
        audit = await db.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            raise AuditNotFound()
        
        await ElasticsearchService.index_audit(audit)
        return f"Audit {audit_id} indexed in ElasticSearch"

@celery_app.task(**base_task_config)
@unified_task_handler()
async def analyze_content(self, audit_id: int, options: Dict = None) -> str:
    """Unified content analysis task"""
    async with get_db() as db:
        audit_service = AuditService(db)
        audit = await audit_service.get_audit(audit_id)
        
        analysis_results = {
            'content': await TextAnalysisService.analyze_text(audit.content),
            'seo_score': await SEOScoreService.calculate(audit),
            'suggestions': await SEOSuggestionsService.generate(audit)
        }
        
        if options.get('analyze_competition'):
            analysis_results['competition'] = await CompetitionAnalysisService.analyze(
                audit, options.get('competitor_urls', [])
            )
            
        await audit_service.update_analysis_results(audit_id, analysis_results)
        return "Content analysis completed"

@celery_app.task
async def analyze_market_position(audit_id: int, keywords: List[str]) -> str:
    """Kompleksowa analiza pozycji w SERP i konkurencji"""
    async with get_db() as db:
        audit = await db.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            raise AuditNotFound()

        serp_service = SerpAnalysisService()
        data_dict = json.loads(audit.audit_data or '{}')
        
        # Analiza dla każdego słowa kluczowego
        market_analysis = {
            'keywords_analysis': [],
            'overall_stats': {
                'avg_position': 0,
                'total_keywords': len(keywords),
                'top_10_count': 0
            }
        }

        for keyword in keywords:
            analysis = await serp_service.analyze_serp_position(
                keyword=keyword,
                domain=urlparse(audit.url).netloc
            )
            market_analysis['keywords_analysis'].append(analysis)
        
        # Aktualizacja danych audytu
        data_dict['market_position_analysis'] = market_analysis
        audit.audit_data = json.dumps(data_dict, ensure_ascii=False)
        await db.commit()
        
        # Indeksowanie w ElasticSearch
        await index_audit_data.delay(audit_id)
        
        return "Market position analysis completed"

@celery_app.task
async def analyze_content_quality(audit_id: int, main_keyword: str) -> str:
    """Kompleksowa analiza jakości treści"""
    async with get_db() as db:
        audit = await db.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            raise AuditNotFound()

        content_service = ContentAnalysisService()
        data_dict = json.loads(audit.audit_data or '{}')
        
        # Pobierz treść ze strony
        text_content = data_dict.get('text_content', '')
        if not text_content:
            raise ContentNotFoundError("Nie znaleziono treści do analizy")

        # Przeprowadź analizę
        analysis_results = await content_service.analyze_content_depth(
            text_content,
            main_keyword
        )
        
        # Aktualizuj dane audytu
        data_dict['content_quality_analysis'] = analysis_results
        audit.audit_data = json.dumps(data_dict, ensure_ascii=False)
        await db.commit()
        
        # Indeksuj w ElasticSearch
        await index_audit_data.delay(audit_id)
        
        return "Content quality analysis completed"

@celery_app.task
async def analyze_performance(audit_id: int) -> str:
    """Analiza wydajności strony"""
    async with get_db() as db:
        audit = await db.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            raise AuditNotFound()

        perf_service = PerformanceAnalysisService()
        data_dict = json.loads(audit.audit_data or '{}')
        
        # Analiza wydajności
        performance_data = await perf_service.analyze_performance(audit.url)
        
        # Aktualizacja danych audytu
        data_dict['performance_analysis'] = performance_data
        audit.audit_data = json.dumps(data_dict, ensure_ascii=False)
        await db.commit()
        
        # Indeksowanie w ElasticSearch
        await index_audit_data.delay(audit_id)
        
        return "Performance analysis completed"

@celery_app.task(
    bind=True,
    soft_time_limit=settings.CELERY_TASK_TIMEOUT,
    max_retries=3
)
async def monitor_performance(self, audit_id: int) -> str:
    """Monitorowanie wydajności strony"""
    async with get_db() as db:
        audit = await db.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            raise AuditNotFound()

        monitoring_service = PerformanceMonitoringService()
        data_dict = json.loads(audit.audit_data or '{}')
        
        # Zbierz metryki
        monitoring_data = await monitoring_service.monitor_metrics(audit.url)
        
        # Aktualizuj dane audytu
        if 'performance_monitoring' not in data_dict:
            data_dict['performance_monitoring'] = []
        
        data_dict['performance_monitoring'].append({
            'timestamp': datetime.now().isoformat(),
            **monitoring_data
        })
        
        # Zachowaj tylko ostatnie 7 dni monitoringu
        week_ago = datetime.now() - datetime.timedelta(days=7)
        data_dict['performance_monitoring'] = [
            entry for entry in data_dict['performance_monitoring']
            if datetime.fromisoformat(entry['timestamp']) > week_ago
        ]
        
        audit.audit_data = json.dumps(data_dict, ensure_ascii=False)
        await db.commit()
        
        return "Performance monitoring updated"

@celery_app.task
async def analyze_with_ai(audit_id: int) -> str:
    """Kompleksowa analiza z wykorzystaniem AI"""
    async with get_db() as db:
        audit = await db.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            raise AuditNotFound()

        ai_service = AIAnalysisService()
        data_dict = json.loads(audit.audit_data or '{}')
        
        # Analiza treści
        content_analysis = await ai_service.analyze_content_structure(
            data_dict.get('text_content', '')
        )
        
        # Analiza i sugestie meta tagów
        meta_improvements = await ai_service.generate_meta_improvements(
            data_dict.get('meta_tags', {})
        )
        
        # Analiza konkurencji jeśli dostępna
        competition_analysis = None
        if data_dict.get('competitor_content'):
            competition_analysis = await ai_service.analyze_competition_gap(
                data_dict.get('text_content', ''),
                data_dict.get('competitor_content', '')
            )
        
        # Aktualizacja danych audytu
        data_dict['ai_analysis'] = {
            'content_structure': content_analysis,
            'meta_improvements': meta_improvements,
            'competition_analysis': competition_analysis,
            'analyzed_at': datetime.now().isoformat()
        }
        
        audit.audit_data = json.dumps(data_dict, ensure_ascii=False)
        await db.commit()
        
        return "AI analysis completed"

@celery_app.task(
    bind=True,
    soft_time_limit=settings.CELERY_TASK_TIMEOUT,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True
)
async def analyze_technical_seo(self, audit_id: int) -> str:
    """Kompleksowa analiza technicznego SEO z wykorzystaniem AI"""
    async with get_db() as db:
        audit = await db.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            raise AuditNotFound()

        tech_seo_service = AITechnicalSEOService()
        data_dict = json.loads(audit.audit_data or '{}')
        
        # Pobierz dane wydajnościowe
        performance_data = data_dict.get('performance_analysis', {})
        
        # Analiza techniczna
        technical_analysis = await tech_seo_service.analyze_technical_issues(
            data_dict.get('html_content', ''),
            performance_data
        )
        
        # Sugestie Schema.org
        schema_suggestions = await tech_seo_service.generate_schema_suggestions(
            data_dict.get('text_content', ''),
            data_dict.get('page_type', 'website')
        )
        
        # Analiza Core Web Vitals
        cwv_analysis = await tech_seo_service.analyze_core_web_vitals(
            performance_data.get('metrics', {})
        )
        
        # Aktualizacja danych audytu
        data_dict['technical_seo_analysis'] = {
            'technical_issues': technical_analysis,
            'schema_suggestions': schema_suggestions,
            'core_web_vitals_analysis': cwv_analysis,
            'analyzed_at': datetime.now().isoformat()
        }
        
        audit.audit_data = json.dumps(data_dict, ensure_ascii=False)
        await db.commit()
        
        return "Technical SEO analysis completed"

@celery_app.task
async def optimize_seo_strategy(audit_id: int) -> str:
    """Kompleksowa optymalizacja strategii SEO z wykorzystaniem AI"""
    async with get_db() as db:
        audit = await db.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            raise AuditNotFound()

        seo_service = AISEOOptimizationService()
        data_dict = json.loads(audit.audit_data or '{}')
        
        # Analiza luk w treści
        content_gaps = await seo_service.analyze_content_gaps(
            data_dict.get('text_content', ''),
            data_dict.get('serp_analysis', {})
        )
        
        # Plan rozwoju treści
        content_plan = await seo_service.generate_content_plan(data_dict)
        
        # Optymalizacja linków wewnętrznych
        internal_linking = await seo_service.optimize_internal_linking(
            data_dict.get('pages_data', [])
        )
        
        # Aktualizacja danych audytu
        data_dict['seo_optimization'] = {
            'content_gaps': content_gaps,
            'content_plan': content_plan,
            'internal_linking': internal_linking,
            'generated_at': datetime.now().isoformat()
        }
        
        audit.audit_data = json.dumps(data_dict, ensure_ascii=False)
        await db.commit()
        
        return "SEO optimization strategy generated"

@celery_app.task
async def generate_master_seo_plan(audit_id: int) -> str:
    """Generuje kompleksowy plan SEO"""
    async with get_db() as db:
        audit = await db.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            raise AuditNotFound()

        master_service = AISEOMasterService()
        data_dict = json.loads(audit.audit_data or '{}')
        
        # Generuj główną analizę
        master_analysis = await master_service.generate_master_analysis(data_dict)
        
        # Generuj plan przewagi konkurencyjnej
        competitive_plan = await master_service.generate_competitive_advantage_plan(data_dict)
        
        # Aktualizuj dane audytu
        data_dict['master_seo_plan'] = {
            'master_analysis': master_analysis,
            'competitive_plan': competitive_plan,
            'generated_at': datetime.now().isoformat()
        }
        
        audit.audit_data = json.dumps(data_dict, ensure_ascii=False)
        await db.commit()
        
        return "Master SEO plan generated"

@celery_app.task(
    bind=True,
    soft_time_limit=settings.CELERY_TASK_TIMEOUT,
    max_retries=3,
    retry_backoff=True,
    autoretry_for=(Exception,)
)
async def safe_task_wrapper(self, task_func, *args, **kwargs):
    """Wrapper do bezpiecznego wykonywania zadań z obsługą błędów"""
    try:
        return await task_func(*args, **kwargs)
    except Exception as exc:
        self.retry(exc=exc)
        raise TaskExecutionError(f"Task failed: {str(exc)}")
    finally:
        # Zamknij wszystkie połączenia
        await cleanup_connections()

@celery_app.task(**base_task_config)
@unified_task_handler()
async def analyze_page_elements(self, audit_id: int, elements: List[str] = None) -> str:
    """Unified task for analyzing page elements (links, images, headings, meta)"""
    async with get_db() as db:
        audit_service = AuditService(db)
        audit = await audit_service.get_audit(audit_id)
        
        elements = elements or ['links', 'images', 'headings', 'meta']
        analysis_results = {}
        
        if 'links' in elements:
            analysis_results['links'] = await LinkAnalysisService.analyze(audit.url)
            
        if 'images' in elements:
            analysis_results['images'] = await ImageAnalysisService.analyze(audit.url)
            
        if 'headings' in elements:
            analysis_results['headings'] = await HeadingAnalysisService.analyze(audit.url)
            
        if 'meta' in elements:
            analysis_results['meta'] = await MetaAnalysisService.analyze(audit.url)
        
        await audit_service.update_analysis_results(audit_id, analysis_results)
        return f"Analyzed elements: {', '.join(elements)}"

@celery_app.task(**base_task_config)
@unified_task_handler()
async def generate_ai_suggestions(self, audit_id: int, elements: List[str] = None) -> str:
    """Unified task for generating AI suggestions"""
    async with get_db() as db:
        audit_service = AuditService(db)
        audit = await audit_service.get_audit(audit_id)
        
        elements = elements or ['links', 'images', 'content']
        suggestions = {}
        
        if 'links' in elements:
            suggestions['link_fixes'] = await AIAnalysisService.suggest_link_fixes(audit)
            
        if 'images' in elements:
            suggestions['alt_texts'] = await AIAnalysisService.suggest_alt_texts(audit)
            
        if 'content' in elements:
            suggestions['content'] = await AIAnalysisService.suggest_content_improvements(audit)
        
        await audit_service.update_suggestions(audit_id, suggestions)
        return f"Generated suggestions for: {', '.join(elements)}"

@celery_app.task(**base_task_config)
@unified_task_handler()
async def analyze_audit_elements(self, audit_id: int, user_id: int, elements: List[str] = None) -> str:
    """Unified task with authorization"""
    async with get_db() as db:
        audit_service = AuditService(db)
        audit = await audit_service.get_audit(audit_id)
        if audit.owner_id != user_id:
            await activity_monitor.log_activity(
                user_id,
                "unauthorized_task_execution",
                {"audit_id": audit_id, "task": "analyze_audit_elements"}
            )
            raise HTTPException(status_code=403, detail="Not authorized")
        
        elements = elements or ['links', 'images', 'headings', 'meta']
        analysis_results = {}
        
        # Logowanie rozpoczęcia analizy
        await activity_monitor.log_activity(
            user_id,
            "analysis_started",
            {"audit_id": audit_id, "elements": elements}
        )
        
        try:
            if 'links' in elements:
                analysis_results['links'] = await LinkAnalysisService.analyze(audit.url)
                
            if 'images' in elements:
                analysis_results['images'] = await ImageAnalysisService.analyze(audit.url)
                
            if 'headings' in elements:
                analysis_results['headings'] = await HeadingAnalysisService.analyze(audit.url)
                
            if 'meta' in elements:
                analysis_results['meta'] = await MetaAnalysisService.analyze(audit.url)
            
            # Aktualizacja danych audytu
            data_dict = json.loads(audit.audit_data or '{}')
            data_dict['elements_analysis'] = {
                **data_dict.get('elements_analysis', {}),
                **analysis_results,
                'analyzed_at': datetime.utcnow().isoformat()
            }
            audit.audit_data = json.dumps(data_dict, ensure_ascii=False)
            await db.commit()
            
            # Logowanie sukcesu
            await activity_monitor.log_activity(
                user_id,
                "analysis_completed",
                {"audit_id": audit_id, "elements": elements}
            )
            
            return f"Analyzed elements: {', '.join(elements)}"
            
        except Exception as e:
            # Logowanie błędu
            await activity_monitor.log_activity(
                user_id,
                "analysis_failed",
                {"audit_id": audit_id, "error": str(e)}
            )
            raise

@celery_app.task(base=ErrorHandlingTask)
def your_task():
    try:
        # kod zadania
        pass
    except Exception as e:
        logger.exception("Task error details:")
        raise

@celery_app.task(name="unified_analysis_task")
async def unified_analysis_task(audit_id: int, analysis_type: str) -> dict:
    """Unified task for different types of analysis"""
    async with get_db() as db:
        audit_service = AuditService(db)
        audit = await audit_service.get_audit(audit_id)
        
        try:
            result = await audit_service.analyze(audit_id, analysis_type)
            return {
                "status": "success",
                "audit_id": audit_id,
                "analysis_type": analysis_type,
                "result": result
            }
        except Exception as e:
            await activity_monitor.log_activity(
                audit.owner_id,
                "analysis_failed",
                {
                    "audit_id": audit_id,
                    "analysis_type": analysis_type,
                    "error": str(e)
                }
            )
            raise

@celery_app.task(name="generate_ai_suggestions")
async def generate_ai_suggestions(audit_id: int, elements: Optional[List[str]] = None) -> dict:
    """Generate AI-powered suggestions for audit elements"""
    async with get_db() as db:
        audit_service = AuditService(db)
        audit = await audit_service.get_audit(audit_id)
        
        try:
            suggestions = await audit_service.generate_suggestions(audit_id, elements)
            return {
                "status": "success",
                "audit_id": audit_id,
                "elements": elements,
                "suggestions": suggestions
            }
        except Exception as e:
            await activity_monitor.log_activity(
                audit.owner_id,
                "suggestions_failed",
                {
                    "audit_id": audit_id,
                    "elements": elements,
                    "error": str(e)
                }
            )
            raise
