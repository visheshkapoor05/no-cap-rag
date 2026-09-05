"""
The office's front door: assembles the operating manual, wires up the
paper-trail middleware and error policy, and mounts every desk (router)
that's open for business so far. See ../ANALOGY.md.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestLoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Office workflow:
      1. Open the doors: configure logging once, before anything else runs.
      2. (Later milestones open the archive room and filing cabinets here —
         Postgres, Milvus, Redis connections — once at startup, not once
         per visitor.)
      3. Hand control to the running office for as long as it's open.
      4. Close the doors cleanly on shutdown.
    """
    settings = get_settings()
    configure_logging(settings.log_level)
    yield


def create_app() -> FastAPI:
    """Builds one FastAPI office, ready to have desks mounted onto it."""
    app = FastAPI(title="Research Bureau", lifespan=lifespan)
    app.add_middleware(RequestLoggingMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router)
    return app


app = create_app()
