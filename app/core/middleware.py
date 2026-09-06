"""
The front desk: stamps a ticket number on every visitor before they're let
in, and logs when they arrived and when they left. See ../../ANALOGY.md.
"""
import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logging import bind_request_id

logger = logging.getLogger("app.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Office workflow, once per visitor:
      1. Issue a ticket number (or reuse one the visitor already carries,
         e.g. handed down from an upstream gateway) and attach it to
         everything logged for the rest of this request.
      2. Log that the visit started, before any real work happens.
      3. Let the request through to whichever desk actually handles it.
      4. Log that the visit finished — how long it took, and whether it
         ended in an error. This one line is what later milestones' tracing
         and cost/latency work builds on top of.
    """

    async def dispatch(self, request: Request, call_next):
        ticket = bind_request_id(request.headers.get("x-request-id"))
        started_at = time.perf_counter()

        logger.info("request started", extra={"path": request.url.path, "method": request.method})

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - started_at) * 1000
            logger.exception("request failed", extra={"duration_ms": round(duration_ms, 2)})
            raise

        duration_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "request finished",
            extra={"status_code": response.status_code, "duration_ms": round(duration_ms, 2)},
        )
        response.headers["x-request-id"] = ticket
        return response
