"""
API v1 router configuration
"""

from fastapi import APIRouter
from .endpoints import auth, schedule

api_router = APIRouter()

# Include authentication routes
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)

# Include schedule routes
api_router.include_router(
    schedule.router,
    prefix="/schedule",
    tags=["schedule"]
)
