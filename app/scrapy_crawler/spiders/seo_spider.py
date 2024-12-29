from scrapy import Spider, Request
from urllib.parse import urljoin, urlparse
from typing import Dict, Any, Generator

class SEOSpider(Spider):
    name = 'seo_spider'
    custom_settings = {
        'CONCURRENT_REQUESTS': 16,
        'DOWNLOAD_DELAY': 0.5,
        'ROBOTSTXT_OBEY': True,
        'COOKIES_ENABLED': False,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 3,
        'DOWNLOAD_TIMEOUT': 15,
    }
    
    def __init__(self, start_url: str, max_pages: int = 30, depth_limit: int = 2, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = [start_url]
        self.max_pages = max_pages
        self.depth_limit = depth_limit
        self.base_domain = urlparse(start_url).netloc
        self.visited_count = 0
        self.visited_urls = set()

    def parse(self, response) -> Generator[Dict[str, Any], None, None]:
        if self.visited_count >= self.max_pages:
            return

        self.visited_count += 1
        
        # Zbieramy dane SEO
        data = {
            'url': response.url,
            'status_code': response.status,
            'title': response.css('title::text').get(),
            'meta_description': response.css('meta[name="description"]::attr(content)').get(),
            'h1_tags': response.css('h1::text').getall(),
            'images': [
                {
                    'src': img.attrib.get('src'),
                    'alt': img.attrib.get('alt')
                } for img in response.css('img')
            ],
            'links': [
                {
                    'url': urljoin(response.url, a.attrib.get('href')),
                    'text': a.css('::text').get()
                } for a in response.css('a[href]')
            ]
        }
        
        yield data

        # Crawl linków wewnętrznych
        if self.visited_count < self.max_pages:
            for link in response.css('a[href]'):
                url = urljoin(response.url, link.attrib.get('href'))
                if urlparse(url).netloc == self.base_domain:
                    yield Request(url, callback=self.parse) 