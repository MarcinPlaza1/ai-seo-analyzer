from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from contextlib import contextmanager
from typing import Generator, Dict, Any

class SeleniumBrowser:
    def __init__(self, headless: bool = True):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        
    def get_page_data(self, url: str, wait_time: int = 5) -> Dict[str, Any]:
        self.driver.get(url)
        WebDriverWait(self.driver, wait_time).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        return {
            'url': url,
            'title': self.driver.title,
            'meta_description': self._get_meta_description(),
            'h1_tags': self._get_elements_text('h1'),
            'links': self._get_links(),
            'images': self._get_images()
        }
    
    def _get_meta_description(self) -> str:
        meta = self.driver.find_elements(By.CSS_SELECTOR, 'meta[name="description"]')
        return meta[0].get_attribute('content') if meta else None
        
    def _get_elements_text(self, tag: str) -> list:
        elements = self.driver.find_elements(By.TAG_NAME, tag)
        return [el.text for el in elements if el.text.strip()]
        
    def _get_links(self) -> list:
        links = self.driver.find_elements(By.TAG_NAME, 'a')
        return [{'url': link.get_attribute('href'), 'text': link.text}
                for link in links if link.get_attribute('href')]
                
    def _get_images(self) -> list:
        images = self.driver.find_elements(By.TAG_NAME, 'img')
        return [{'src': img.get_attribute('src'), 'alt': img.get_attribute('alt')}
                for img in images if img.get_attribute('src')]
    
    def close(self):
        if self.driver:
            self.driver.quit()

@contextmanager
def get_browser(headless: bool = True) -> Generator[SeleniumBrowser, None, None]:
    browser = SeleniumBrowser(headless)
    try:
        yield browser
    finally:
        browser.close() 