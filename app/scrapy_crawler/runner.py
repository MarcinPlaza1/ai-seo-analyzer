from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
from twisted.internet import reactor
from typing import Dict, List, Any
from .spiders.seo_spider import SEOSpider
from ..selenium_crawler.browser import get_browser

class ScrapyRunner:
    def __init__(self, use_selenium: bool = False):
        self.use_selenium = use_selenium
        self.settings = get_project_settings()
        self.runner = CrawlerRunner(self.settings)
        self.results: List[Dict[str, Any]] = []

    async def crawl(self, url: str, max_pages: int = 30, depth_limit: int = 2) -> List[Dict[str, Any]]:
        if self.use_selenium:
            with get_browser() as browser:
                return [browser.get_page_data(url)]
        else:
            def _crawl():
                d = self.runner.crawl(
                    SEOSpider,
                    start_url=url,
                    max_pages=max_pages,
                    depth_limit=depth_limit
                )
                return d
            
            await reactor.callFromThread(_crawl)
            return self.results 