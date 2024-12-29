from typing import Dict, Any
from datetime import datetime
import json
from app.core.redis_client import redis_client, get_redis_client
from app.models.user import User

class ActivityMonitor:
    SUSPICIOUS_PATTERNS = {
        'multiple_failed_logins': 5,
        'rapid_requests': 50,
        'api_abuse': 100
    }

    def __init__(self, redis_client=None):
        """Inicjalizuje monitor aktywności z opcjonalnym klientem Redis"""
        self.redis_client = redis_client or get_redis_client()

    async def log_activity(self, user_id: int, action: str, details: Dict[str, Any]) -> None:
        activity = {
            'timestamp': datetime.utcnow().isoformat(),
            'action': action,
            'details': details,
            'ip': details.get('ip'),
            'user_agent': details.get('user_agent')
        }
        
        key = f"user_activity:{user_id}"
        self.redis_client.lpush(key, json.dumps(activity))
        self.redis_client.ltrim(key, 0, 999)  # Zachowaj ostatnie 1000 aktywności
        
        await self.check_suspicious_activity(user_id, action, details)
    
    async def check_suspicious_activity(self, user_id: int, action: str, details: Dict) -> None:
        if await self._is_suspicious_pattern(user_id, action, details):
            await self._handle_suspicious_activity(user_id, action, details)

    async def _is_suspicious_pattern(self, user_id: int, action: str, details: Dict) -> bool:
        """Sprawdza czy aktywność użytkownika pasuje do wzorców podejrzanych zachowań"""
        key = f"user_activity:{user_id}"
        recent_activities = self.redis_client.lrange(key, 0, 99)  # Sprawdź ostatnie 100 aktywności
        
        if not recent_activities:
            return False
            
        activities = [json.loads(activity) for activity in recent_activities]
        
        # Sprawdź wzorce podejrzanych zachowań
        if action == 'login_failed':
            failed_logins = sum(1 for a in activities 
                              if a['action'] == 'login_failed' 
                              and (datetime.utcnow() - datetime.fromisoformat(a['timestamp'])).seconds < 300)
            if failed_logins >= self.SUSPICIOUS_PATTERNS['multiple_failed_logins']:
                return True
                
        # Sprawdź częstotliwość requestów
        recent_requests = sum(1 for a in activities 
                            if (datetime.utcnow() - datetime.fromisoformat(a['timestamp'])).seconds < 60)
        if recent_requests >= self.SUSPICIOUS_PATTERNS['rapid_requests']:
            return True
            
        return False

    async def _handle_suspicious_activity(self, user_id: int, action: str, details: Dict) -> None:
        """Obsługuje wykryte podejrzane zachowania"""
        alert = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'action': action,
            'details': details,
            'type': 'suspicious_activity'
        }
        
        # Zapisz alert w Redis
        self.redis_client.lpush('security_alerts', json.dumps(alert))
        
        # Możesz dodać dodatkowe działania, np. blokowanie użytkownika, wysyłanie powiadomień, itp.
        if action == 'login_failed':
            self.redis_client.setex(f"user_blocked:{user_id}", 300, "1")  # Blokuj na 5 minut 