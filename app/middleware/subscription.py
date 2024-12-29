from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.models.user import User, SubscriptionTier
from datetime import datetime

class SubscriptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if hasattr(request.state, "user") and isinstance(request.state.user, User):
            user = request.state.user
            
            # Sprawdź czy subskrypcja jest aktywna
            if user.subscription_tier != SubscriptionTier.FREE:
                if not user.is_subscription_active():
                    # Degraduj do darmowego planu
                    user.subscription_tier = SubscriptionTier.FREE
                    # TODO: Zaktualizuj w bazie danych
                    
                    return JSONResponse(
                        status_code=402,
                        content={
                            "detail": "Your premium subscription has expired",
                            "code": "subscription_expired"
                        }
                    )
        
        response = await call_next(request)
        return response 