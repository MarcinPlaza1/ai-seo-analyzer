from fastapi import Request
from time import time
from ..monitoring import REQUEST_TIME

async def monitoring_middleware(request: Request, call_next):
    start_time = time()
    response = await call_next(request)
    duration = time() - start_time
    
    REQUEST_TIME.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response 