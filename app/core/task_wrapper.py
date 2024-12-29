from functools import wraps
from typing import Callable, Any
from .error_handling import handle_task_error, TaskExecutionError
from .rate_limiter import RateLimiter
from .cache_manager import CacheManager
from ..database_utils import get_db

rate_limiter = RateLimiter()
cache_manager = CacheManager()

def unified_task_handler():
    def decorator(task_func: Callable) -> Callable:
        @wraps(task_func)
        async def wrapper(*args, **kwargs) -> Any:
            task_name = task_func.__name__
            cache_key = f"{task_name}:{args}:{kwargs}"

            try:
                # Sprawdź cache
                if cached_result := await cache_manager.get_cached(cache_key):
                    return cached_result

                # Sprawdź rate limit
                await rate_limiter.wait_for_slot(task_name)

                # Wykonaj zadanie
                async with get_db() as db:
                    result = await task_func(*args, **kwargs)
                    
                    # Cache wynik
                    await cache_manager.set_cached(cache_key, result)
                    
                    return result

            except Exception as exc:
                error_details = await handle_task_error(task_name, exc)
                raise TaskExecutionError(
                    message=f"Task {task_name} failed",
                    error_code="TASK_EXECUTION_ERROR",
                    details=error_details
                )

        return wrapper
    return decorator 