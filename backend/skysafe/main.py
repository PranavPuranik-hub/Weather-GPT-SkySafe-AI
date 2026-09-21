"""
FastAPI Main Application Entrypoint for SkySafe AI.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from skysafe.core.config import settings
from skysafe.api import health_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Action-intelligence layer for official weather warnings and climate information."
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

@app.get("/")
def root():
    return {
        "message": "Welcome to SkySafe AI API",
        "docs": "/docs",
        "health": "/health"
    }
