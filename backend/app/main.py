from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.routers import health, rfp
from app.api.e1_router import router as e1_router
from app.api.e2_routes import router as e2_router
from app.api.e3_routes import router as e3_router
from app.api.e4_routes import router as e4_router
from app.api.e5_routes import router as e5_router
from app.config import get_settings

BOMATIC_API_KEY = get_settings().bomatic_api_key
if not BOMATIC_API_KEY:
    raise RuntimeError("BOMATIC_API_KEY environment variable is not set. Set it in backend/.env before starting the server.")
_EXCLUDED_PATHS = {"/docs", "/health", "/openapi.json", "/redoc"}


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path not in _EXCLUDED_PATHS:
            if request.headers.get("X-API-Key") != BOMATIC_API_KEY:
                return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
        return await call_next(request)


app = FastAPI(
    title="BOMATIC",
    description="Pre-Sales Engineering Assistant — RFP Parser + Compliance Matrix Engine",
    version="0.1.0",
)

app.add_middleware(APIKeyMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(rfp.router, prefix="/api/v1")
app.include_router(e1_router, prefix="/api")
app.include_router(e2_router, prefix="/api")
app.include_router(e3_router, prefix="/api")
app.include_router(e4_router, prefix="/api")
app.include_router(e5_router, prefix="/api")
