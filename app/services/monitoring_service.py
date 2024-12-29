from typing import Dict, List
import asyncio
import aiohttp
from datetime import datetime, timedelta
import pandas as pd
from ..config.settings import settings
from ..models.monitoring import MonitoringMetrics

class PerformanceMonitoringService:
    def __init__(self):
        self.metrics_history = []
        
    async def monitor_metrics(self, url: str, interval: int = 300) -> Dict:
        """Monitoruje metryki wydajności co określony interwał (w sekundach)"""
        metrics = await self._collect_metrics(url)
        self.metrics_history.append({
            'timestamp': datetime.now(),
            **metrics
        })
        
        # Usuń stare metryki (starsze niż 7 dni)
        self._cleanup_old_metrics()
        
        return {
            'current_metrics': metrics,
            'trends': self._calculate_trends(),
            'alerts': self._check_alerts(metrics)
        }
    
    async def _collect_metrics(self, url: str) -> Dict:
        async with aiohttp.ClientSession() as session:
            start_time = datetime.now()
            async with session.get(url) as response:
                response_time = (datetime.now() - start_time).total_seconds()
                
                return {
                    'response_time': response_time,
                    'status_code': response.status,
                    'content_length': len(await response.text()),
                    'headers': dict(response.headers)
                }
    
    def _calculate_trends(self) -> Dict:
        """Oblicza trendy na podstawie historycznych danych"""
        if not self.metrics_history:
            return {}
            
        df = pd.DataFrame(self.metrics_history)
        
        return {
            'response_time_trend': self._calculate_metric_trend(df, 'response_time'),
            'content_length_trend': self._calculate_metric_trend(df, 'content_length'),
            'availability': self._calculate_availability(df)
        }
    
    def _check_alerts(self, metrics: Dict) -> List[Dict]:
        """Sprawdza czy metryki przekraczają ustalone progi"""
        alerts = []
        
        if metrics['response_time'] > settings.RESPONSE_TIME_THRESHOLD:
            alerts.append({
                'level': 'warning',
                'message': f'Response time ({metrics["response_time"]:.2f}s) exceeds threshold',
                'timestamp': datetime.now()
            })
            
        return alerts 