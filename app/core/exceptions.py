"""
Office policy for handling things going wrong: turns a failure into a
structured, visitor-facing error instead of a stack trace. See
../../ANALOGY.md.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("app.errors")


class AppError(Exception):
    """Base class for errors the office recognizes and knows how to explain."""

    status_code = 500
    code = "internal_error"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    """Raised when a visitor asks for a case file that doesn't exist."""

    status_code = 404
    code = "not_found"


def register_exception_handlers(app: FastAPI) -> None:
    """
    Office workflow when something goes wrong:
      1. If it's an error the office has a name for (an AppError), report it
         back to the visitor with that name and message at the right status
         code, and log it at a level matching how expected it was.
      2. If it's anything else — a bug — never leak the internals to the
         visitor. Log the full detail for the office's own record, and hand
         the visitor a generic "something went wrong" instead.
    """

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning("handled error", extra={"code": exc.code, "path": request.url.path})
        return JSONResponse(status_code=exc.status_code, content={"code": exc.code, "message": exc.message})

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error", extra={"path": request.url.path})
        return JSONResponse(
            status_code=500,
            content={"code": "internal_error", "message": "Something went wrong on our side."},
        )
