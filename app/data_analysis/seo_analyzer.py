import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Any
from urllib.parse import urlparse
import json
import io
import base64

class SEODataAnalyzer:
    def __init__(self, audit_data: Dict[str, Any]):
        self.audit_data = audit_data
        self.df_links = self._prepare_links_df()
        self.df_images = self._prepare_images_df()
        self.df_headings = self._prepare_headings_df()
    
    def _prepare_links_df(self) -> pd.DataFrame:
        links = self.audit_data.get('links', [])
        return pd.DataFrame(links)
    
    def _prepare_images_df(self) -> pd.DataFrame:
        images = self.audit_data.get('images', [])
        return pd.DataFrame(images)
    
    def _prepare_headings_df(self) -> pd.DataFrame:
        headings = self.audit_data.get('headings', {})
        return pd.DataFrame({
            'type': ['h1', 'h2', 'h3'],
            'count': [
                len(headings.get('h1', [])),
                len(headings.get('h2', [])),
                len(headings.get('h3', []))
            ]
        })
    
    def generate_link_stats(self) -> Dict[str, Any]:
        if self.df_links.empty:
            return {}
            
        stats = {
            'total_links': len(self.df_links),
            'unique_domains': self.df_links['url'].apply(lambda x: urlparse(x).netloc).nunique(),
            'status_distribution': self.df_links['status_code'].value_counts().to_dict(),
            'avg_text_length': int(self.df_links['text'].str.len().mean())
        }
        return stats
    
    def generate_image_stats(self) -> Dict[str, Any]:
        if self.df_images.empty:
            return {}
            
        stats = {
            'total_images': len(self.df_images),
            'missing_alt': int(self.df_images['alt'].isna().sum()),
            'avg_alt_length': int(self.df_images['alt'].str.len().mean())
        }
        return stats
    
    def generate_visualizations(self) -> Dict[str, str]:
        """Generuje wykresy jako base64 strings"""
        visualizations = {}
        
        # Wykres statusów linków
        plt.figure(figsize=(10, 6))
        self.df_links['status_code'].value_counts().plot(kind='bar')
        plt.title('Link Status Distribution')
        visualizations['link_status'] = self._fig_to_base64()
        
        # Wykres nagłówków
        plt.figure(figsize=(8, 5))
        self.df_headings.plot(x='type', y='count', kind='bar')
        plt.title('Heading Distribution')
        visualizations['headings'] = self._fig_to_base64()
        
        return visualizations
    
    def _fig_to_base64(self) -> str:
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        return base64.b64encode(buf.getvalue()).decode() 