"""
Request Correlation and Structured Logging Middleware.

Provides:
1. X-Request-ID generation and propagation across HTTP requests and responses.
2. Context variable tracking for logging request correlation IDs.
3. Sensitive credential masking in logs (passwords, JWTs, refresh tokens).
"""

import re
import uuid
import logging
from contextvars import ContextVar
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Request correlation ID context variable for the current request
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """Return the current correlation request ID or empty string."""
    return request_id_ctx.get()


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """
    Extracts an incoming X-Request-ID or generates a new UUID v4.
    Attaches the correlation ID to the response headers and context.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        incoming_req_id = request.headers.get("X-Request-ID")
        if incoming_req_id and incoming_req_id.strip():
            req_id = incoming_req_id.strip()
        else:
            req_id = str(uuid.uuid4())

        token = request_id_ctx.set(req_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            request_id_ctx.reset(token)


class RequestIdFilter(logging.Filter):
    """
    Log filter that attaches the current request correlation ID to log records.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True


class SensitiveDataFilter(logging.Filter):
    """
    Log filter that redacts raw passwords, JWTs, refresh tokens, and bearer credentials
    from log messages before output.
    """

    PATTERNS = [
        (re.compile(r'("password"\s*:\s*)"([^"]*)"', re.IGNORECASE), r'\1"[REDACTED]"'),
        (re.compile(r'("access_token"\s*:\s*)"([^"]*)"', re.IGNORECASE), r'\1"[REDACTED]"'),
        (re.compile(r'("refresh_token"\s*:\s*)"([^"]*)"', re.IGNORECASE), r'\1"[REDACTED]"'),
        (re.compile(r'("token"\s*:\s*)"([^"]*)"', re.IGNORECASE), r'\1"[REDACTED]"'),
        (re.compile(r'(Bearer\s+)[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*', re.IGNORECASE), r'\1[REDACTED]'),
        (re.compile(r'(password=)[^\s&]+', re.IGNORECASE), r'\1[REDACTED]'),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            msg = record.msg
            for pattern, repl in self.PATTERNS:
                msg = pattern.sub(repl, msg)
            record.msg = msg
        return True
