from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import os
import asyncio
from contextlib import asynccontextmanager

from app.api.endpoints import router as api_router
from app.config import RETENTION_CLEANUP_INTERVAL_SECONDS, SETTINGS
from app.core.retention import cleanup_expired_artifacts


async def _retention_worker() -> None:
    while True:
        await asyncio.sleep(RETENTION_CLEANUP_INTERVAL_SECONDS)
        cleanup_expired_artifacts()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    cleanup_expired_artifacts()
    worker = asyncio.create_task(_retention_worker())
    try:
        yield
    finally:
        worker.cancel()
        try:
            await worker
        except asyncio.CancelledError:
            pass

app = FastAPI(
    title="SYNOPSIZE Engine API",
    description="Universal Document Intelligence Engine Backend API",
    version="1.0.0",
    lifespan=lifespan,
)

configured_origins = SETTINGS["security"]["cors_allowed_origins"]
cors_origins = [
    origin.strip()
    for origin in os.environ.get(
        "SYNOPSIZE_CORS_ORIGINS", ",".join(configured_origins)
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# Simple rate limiting middleware simulation
REQUEST_TIMES = {}

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()
    
    # Clean up old timestamps (older than 60 sec)
    timestamps = [t for t in REQUEST_TIMES.get(client_ip, []) if now - t < 60]
    if len(timestamps) >= int(SETTINGS["security"]["rate_limit_per_minute"]):
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Please wait a moment before sending more requests."}
        )
    timestamps.append(now)
    REQUEST_TIMES[client_ip] = timestamps
    
    response = await call_next(request)
    return response

# Include main router under /api
app.include_router(api_router, prefix="/api")

@app.get("/")
def root():
    return {
        "engine": "SYNOPSIZE Universal Document Intelligence Engine",
        "status": "online",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
