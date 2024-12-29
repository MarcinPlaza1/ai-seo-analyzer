from typing import Dict, List
import aiohttp
import pandas as pd
import plotly.express as px
import pylighthouse
from ..config.settings import settings

class PerformanceAnalysisService:
    def __init__(self):
        self.lighthouse = pylighthouse.PyLighthouse()
        
    async def analyze_performance(self, url: str) -> Dict:
        """Analiza wydajności strony z wykorzystaniem Lighthouse"""
        results = self.lighthouse.run(
            url,
            categories=['performance', 'seo', 'best-practices']
        )
        
        metrics = {
            'performance_score': results['categories']['performance']['score'] * 100,
            'seo_score': results['categories']['seo']['score'] * 100,
            'best_practices_score': results['categories']['best-practices']['score'] * 100,
            'metrics': {
                'first_contentful_paint': results['audits']['first-contentful-paint']['numericValue'],
                'speed_index': results['audits']['speed-index']['numericValue'],
                'largest_contentful_paint': results['audits']['largest-contentful-paint']['numericValue'],
                'time_to_interactive': results['audits']['interactive']['numericValue']
            }
        }
        
        return {
            'lighthouse_metrics': metrics,
            'visualizations': self._generate_visualizations(metrics),
            'optimization_suggestions': self._generate_suggestions(metrics)
        }
    
    def _generate_visualizations(self, metrics: Dict) -> Dict:
        """Generowanie wizualizacji wyników"""
        df = pd.DataFrame({
            'Metric': ['Performance', 'SEO', 'Best Practices'],
            'Score': [
                metrics['performance_score'],
                metrics['seo_score'],
                metrics['best_practices_score']
            ]
        })
        
        fig = px.bar(df, x='Metric', y='Score',
                    title='Lighthouse Scores',
                    labels={'Score': 'Score (0-100)'})
        
        return {
            'scores_chart': fig.to_json()
        } 