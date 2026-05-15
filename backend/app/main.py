from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import health, rfp
from app.api.e1_router import router as e1_router

app = FastAPI(
    title="BOMATIC",
    description="Pre-Sales Engineering Assistant — RFP Parser + Compliance Matrix Engine",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(rfp.router, prefix="/api/v1")
app.include_router(e1_router, prefix="/api")
