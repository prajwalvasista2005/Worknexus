"""
In-Memory Sliding Window Rate Limiting Middleware.

Enforces per-IP sliding window rate limits on sensitive authentication endpoints:
- POST /api/v1/auth/login & /auth/login: 5 req / min
- POST /api/v1/auth/register & /auth/register: 5 req / min
- POST /api/v1/auth/refresh & /auth/refresh: 20 req / min

Breaches return HTTP 429 with standard `{"detail": "..."}` error payload and Retry-After header.
"""

import time
import threading
from typing import Dict, List, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from ..config import settings
from .correlation import get_request_id


class RateLimiter:
    """Thread-safe sliding window rate limiter."""

    # Path suffix -> (max_requests, window_seconds)
    DEFAULT_RULES: Dict[str, Tuple[int, int]] = {
        "/auth/login": (5, 60),
        "/auth/register": (5, 60),
        "/auth/refresh": (20, 60),
    }

    def __init__(self, rules: Dict[str, Tuple[int, int]] = None, enabled: bool = None):
        self.rules = rules or self.DEFAULT_RULES
        self._lock = threading.Lock()
        # Key: (ip, rule_path) -> List of timestamp floats
        self._history: Dict[Tuple[str, str], List[float]] = {}
        if enabled is not None:
            self.enabled = enabled
        else:
            self.enabled = getattr(settings, "RATE_LIMITING_ENABLED", True)

    def clear(self):
        """Reset rate limiter state (useful for test isolation)."""
        with self._lock:
            self._history.clear()

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return "127.0.0.1"

    def _match_rule(self, method: str, path: str) -> Tuple[str, int, int]:
        """Matches a request against defined rate-limiting rules."""
        if method.upper() != "POST":
            return "", 0, 0

        clean_path = path.rstrip("/")
        for suffix, (max_req, window_sec) in self.rules.items():
            if clean_path.endswith(suffix):
                return suffix, max_req, window_sec

        return "", 0, 0

    def check_rate_limit(self, request: Request) -> Tuple[bool, int, int]:
        """
        Check if request exceeds rate limit.
        Returns: (is_allowed, retry_after_seconds, max_allowed)
        """
        if not self.enabled:
            return True, 0, 0

        rule_suffix, max_requests, window_seconds = self._match_rule(request.method, request.url.path)
        if not rule_suffix:
            return True, 0, 0

        client_ip = self._get_client_ip(request)
        key = (client_ip, rule_suffix)
        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            history = self._history.get(key, [])
            # Prune timestamps outside current sliding window
            history = [ts for ts in history if ts > window_start]

            if len(history) >= max_requests:
                oldest_in_window = history[0]
                retry_after = max(1, int(oldest_in_window + window_seconds - now) + 1)
                self._history[key] = history
                return False, retry_after, max_requests

            history.append(now)
            self._history[key] = history
            return True, 0, max_requests


rate_limiter_instance = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware applying in-memory sliding window rate limiting.
    """

    def __init__(self, app, limiter: RateLimiter = None):
        super().__init__(app)
        self.limiter = limiter or rate_limiter_instance

    async def dispatch(self, request: Request, call_next) -> Response:
        is_allowed, retry_after, limit = self.limiter.check_rate_limit(request)
        if not is_allowed:
            rid = get_request_id()
            headers = {
                "Retry-After": str(retry_after),
            }
            if rid:
                headers["X-Request-ID"] = rid

            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded: maximum {limit} requests per minute. Try again in {retry_after} seconds."},
                headers=headers,
            )

        return await call_next(request)
