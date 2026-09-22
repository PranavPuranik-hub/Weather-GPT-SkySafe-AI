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
    health_router,
    compose_router,
    voice_router,
    languages_router,
    chat_router,
)
from app.core.config import settings
from app.core.db import Base, engine
from app.ingest.scheduler import start_ingest_scheduler, stop_ingest_scheduler
from app.ingest.service import ingest_service

logger = logging.getLogger("app")


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

# CORS Middleware configuration (OWASP security compliance)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production environment
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


@app.get("/")
def root():
    return {
        "message": "Welcome to SkySafe AI API",
        "docs": "/docs",
        "health": "/health",
        "alerts": "/api/alerts",
    }
