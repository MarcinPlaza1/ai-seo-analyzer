from datetime import datetime, timedelta
from typing import Optional
from app.core.redis_client import redis_client
from app.models.user import User
import json

class SessionManager:
    SESSION_TIMEOUT = 30  # minuty
    
    async def create_session(self, user_id: int, session_id: str) -> None:
        session_data = {
            'user_id': user_id,
            'created_at': datetime.utcnow().isoformat(),
            'last_activity': datetime.utcnow().isoformat()
        }
        redis_client.setex(
            f"session:{session_id}",
            self.SESSION_TIMEOUT * 60,
            json.dumps(session_data)
        )
    
    async def update_session_activity(self, session_id: str) -> None:
        session = redis_client.get(f"session:{session_id}")
        if session:
            session_data = json.loads(session)
            session_data['last_activity'] = datetime.utcnow().isoformat()
            redis_client.setex(
                f"session:{session_id}",
                self.SESSION_TIMEOUT * 60,
                json.dumps(session_data)
            ) 

    async def is_session_valid(self, session_id: str) -> bool:
        session = redis_client.get(f"session:{session_id}")
        if not session:
            return False
        
        try:
            session_data = json.loads(session)
            last_activity = datetime.fromisoformat(session_data['last_activity'])
            time_diff = datetime.utcnow() - last_activity
            return time_diff.total_seconds() < self.SESSION_TIMEOUT * 60
        except (json.JSONDecodeError, KeyError, ValueError):
            return False 