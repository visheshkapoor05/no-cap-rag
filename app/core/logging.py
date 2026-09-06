"""
The paper trail: every request gets a ticket number stamped on every log
line it produces, in a machine-readable format so the whole trail can be
pulled back out later. See ../../ANALOGY.md.
"""
import json
import logging
import sys
import uuid
from contextvars import ContextVar

_request_id: ContextVar[str] = ContextVar("request_id", default="-")

_RESERVED_FIELDS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys())


class JSONFormatter(logging.Formatter):
    """
    Stamps every log line with the current request's ticket number and
    renders the line as one JSON object instead of free-form text.

    Office workflow:
      1. Take whatever the caller logged (the message, the level, which
         module wrote it).
      2. Attach the ticket number for whichever visitor's request is
         currently being handled, so lines from concurrent requests never
         get mixed together when read back.
      3. Attach any extra details the caller passed along (e.g. how long a
         step took) — these don't matter to the visitor but matter a great
         deal when tracing a problem later.
      4. Serialize the whole thing as one line of JSON, so it can be
         queried/filtered by field instead of grepped as plain text.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": _request_id.get(),
        }

        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _RESERVED_FIELDS and key not in payload
        }
        payload.update(extras)

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(level: str) -> None:
    """Points the root logger at the JSON formatter, once, at office-opening time."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


def bind_request_id(value: str | None = None) -> str:
    """Issues a new ticket number for the current request, or accepts one handed in upstream."""
    ticket = value or uuid.uuid4().hex[:12]
    _request_id.set(ticket)
    return ticket
