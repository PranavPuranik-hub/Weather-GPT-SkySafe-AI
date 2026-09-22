"""
API router package initialization.
"""
from skysafe.api.admin import router as admin_router
from skysafe.api.alerts import router as alerts_router
from skysafe.api.health import router as health_router

__all__ = ["admin_router", "alerts_router", "health_router"]
