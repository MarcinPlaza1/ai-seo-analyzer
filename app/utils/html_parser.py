from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import re

class HTMLParser:
    def __init__(self, html: str):
        self.soup = BeautifulSoup(html, 'html.parser')
        
    def get_meta_tags(self) -> Dict[str, str]:
        """Pobiera wszystkie meta tagi ze strony."""
        meta_tags = {}
        for tag in self.soup.find_all('meta'):
            name = tag.get('name', tag.get('property', ''))
            content = tag.get('content', '')
            if name and content:
                meta_tags[name] = content
        return meta_tags
        
    def get_headings(self) -> Dict[str, List[str]]:
        """Pobiera wszystkie nagłówki ze strony."""
        headings = {}
        for i in range(1, 7):
            tag = f'h{i}'
            headings[tag] = [h.get_text(strip=True) for h in self.soup.find_all(tag)]
        return headings
        
    def get_images(self) -> List[Dict[str, str]]:
        """Pobiera wszystkie obrazy ze strony."""
        images = []
        for img in self.soup.find_all('img'):
            image_data = {
                'src': img.get('src', ''),
                'alt': img.get('alt', ''),
                'title': img.get('title', '')
            }
            images.append(image_data)
        return images
        
    def get_links(self) -> List[Dict[str, str]]:
        """Pobiera wszystkie linki ze strony."""
        links = []
        for link in self.soup.find_all('a'):
            link_data = {
                'href': link.get('href', ''),
                'text': link.get_text(strip=True),
                'title': link.get('title', '')
            }
            links.append(link_data)
        return links
        
    def get_text_content(self) -> str:
        """Pobiera cały tekst ze strony."""
        # Usuń skrypty i style
        for script in self.soup(['script', 'style']):
            script.decompose()
        
        # Pobierz tekst
        text = self.soup.get_text()
        
        # Wyczyść tekst
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split('  '))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text 