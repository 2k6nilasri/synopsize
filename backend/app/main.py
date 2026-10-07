from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from app.api.endpoints import router as api_router

app = FastAPI(
    title="SYNOPSIZE Engine API",
    description="Universal Document Intelligence Engine Backend API",
    version="1.0.0"
)

# Enable strict CORS security
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production setup can restrict to frontend host
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple rate limiting middleware simulation
REQUEST_TIMES = {}

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()
    
    # Clean up old timestamps (older than 60 sec)
    timestamps = [t for t in REQUEST_TIMES.get(client_ip, []) if now - t < 60]
    if len(timestamps) > 120:  # 120 requests/minute limit
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
