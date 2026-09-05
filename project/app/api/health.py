"""
The office's very first desk: proves the building is open before anything
else gets built on top of it. See ../../ANALOGY.md.
"""
from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    """A visitor can always ask "are you open?" and get a straight answer."""
    settings = get_settings()
    return {"status": "ok", "environment": settings.environment}
