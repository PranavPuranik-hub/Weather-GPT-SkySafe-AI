"""
FastAPI Main Application Entrypoint for SkySafe AI.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    admin_router,
    alerts_router,
    chat_router,
    compose_router,
    health_router,
    languages_router,
    voice_router,
)
from app.api.decision import router as decision_router
from app.api.eval import router as eval_router
from app.api.reports import router as reports_router
from app.api.sms import router as sms_router
from app.core.config import settings
from app.core.db import Base, engine
from app.ingest.scheduler import start_ingest_scheduler, stop_ingest_scheduler
from app.ingest.service import ingest_service

logger = logging.getLogger("app")

# Install PII-redacting log filter at startup
from app.core.security import install_pii_filter

install_pii_filter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown event management."""
    logger.info("Initializing SkySafe database tables...")
    Base.metadata.create_all(bind=engine)

    # Initial ingestion cycle for fixtures mode
    if settings.MODE == "fixtures":
        logger.info("Running initial fixtures ingestion cycle...")
        ingest_service.ingest_cycle()

    # Start background polling scheduler
    start_ingest_scheduler()
    yield
    # Clean shutdown of scheduler
    stop_ingest_scheduler()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Action-intelligence layer for official weather warnings and climate information.",
    lifespan=lifespan,
)

# CORS Middleware — configure allowed origins
import os

_raw_origins = os.getenv("ALLOWED_ORIGINS", "")
_frontend_url = os.getenv("FRONTEND_URL", "")
_default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]
_allowed_origins = list(dict.fromkeys(
    _default_origins +
    [orig.strip() for orig in _raw_origins.split(",") if orig.strip()] +
    ([_frontend_url.strip()] if _frontend_url.strip() else [])
))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(health_router)
app.include_router(alerts_router)
app.include_router(admin_router)
app.include_router(compose_router)
app.include_router(voice_router)
app.include_router(languages_router)
app.include_router(chat_router)
app.include_router(reports_router)
app.include_router(decision_router)
app.include_router(sms_router)
app.include_router(eval_router)

@app.get("/")
def root():
    return {
        "message": "Welcome to SkySafe AI API",
        "docs": "/docs",
        "health": "/health",
        "alerts": "/api/alerts",
    }
