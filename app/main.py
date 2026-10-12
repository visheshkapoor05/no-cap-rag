"""
The office's front door: assembles the operating manual, wires up the
paper-trail middleware and error policy, and mounts every desk (router)
that's open for business so far. See ../ANALOGY.md.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.retrieve import router as retrieve_router
from app.core.config import get_settings
from app.core.db import close_pool, get_pool
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestLoggingMiddleware
from app.embeddings.gemini import close_embedding_provider, get_embedding_provider
from app.retrieval import close_client, get_client
from app.retrieval.sparse import close_sparse_retriever, get_sparse_retriever


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Office workflow:
      1. Open the doors: configure logging once, before anything else runs.
      2. Open the archive room's connections once, at startup — a
         connection pool (see GLOSSARY.md), not one connection per visitor.
      3. Open the scent-sorted filing cabinet's connection too (T-M3.6) —
         same once-at-startup rule, not once per request. (Redis joins
         here in a later milestone.)
      4. Build the two research assistants once too (T-M3.11): the
         embedding provider (one genai.Client, one cache connection) and
         the BM25 index (tokenizing the whole corpus on the first real
         `/retrieve` call, instead of at startup, would make that one
         visitor wait for everyone else's work).
      5. Hand control to the running office for as long as it's open.
      6. Close every connection cleanly on shutdown.
    """
    settings = get_settings()
    configure_logging(settings.log_level)
    get_pool()
    get_client()
    get_embedding_provider()
    get_sparse_retriever()
    yield
    close_sparse_retriever()
    close_embedding_provider()
    close_client()
    close_pool()


def create_app() -> FastAPI:
    """Builds one FastAPI office, ready to have desks mounted onto it."""
    app = FastAPI(title="no-cap-rag", lifespan=lifespan)
    app.add_middleware(RequestLoggingMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(retrieve_router)
    return app


app = create_app()
