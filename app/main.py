"""
The office's front door: assembles the operating manual, wires up the
paper-trail middleware and error policy, and mounts every desk (router)
that's open for business so far. See ../ANALOGY.md.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.core.config import get_settings
from app.core.db import close_pool, get_pool
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestLoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Office workflow:
      1. Open the doors: configure logging once, before anything else runs.
      2. Open the archive room's connections once, at startup — a
         connection pool (see GLOSSARY.md), not one connection per visitor.
         (Milvus/Redis join here in later milestones.)
      3. Hand control to the running office for as long as it's open.
      4. Close the archive room's connections cleanly on shutdown.
    """
    settings = get_settings()
    configure_logging(settings.log_level)
    get_pool()
    yield
    close_pool()


def create_app() -> FastAPI:
    """Builds one FastAPI office, ready to have desks mounted onto it."""
    app = FastAPI(title="no-cap-rag", lifespan=lifespan)
    app.add_middleware(RequestLoggingMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(documents_router)
    return app


app = create_app()
