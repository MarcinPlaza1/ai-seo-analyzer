BOT_NAME = 'seo_mvp'

SPIDER_MODULES = ['app.scrapy_crawler.spiders']
NEWSPIDER_MODULE = 'app.scrapy_crawler.spiders'

USER_AGENT = 'SEO-MVP-Crawler/1.0'

ROBOTSTXT_OBEY = True
CONCURRENT_REQUESTS = 8
DOWNLOAD_DELAY = 1 