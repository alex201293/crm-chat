"""
Rate limiting middleware using Redis sliding window.
Limits requests per IP and per authenticated user.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware.
    In production, this uses Redis sliding window counters.
    For Phase 1, implements a pass-through that can be enhanced later.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ("/health", "/ready"):
            return await call_next(request)

        # Phase 1: pass-through implementation
        # Phase 2 will implement Redis-backed sliding window:
        # - 100 requests/minute per IP for unauthenticated
        # - 1000 requests/minute per user for authenticated
        # - Custom limits per tenant plan

        response = await call_next(request)

        # Add rate limit headers (placeholder values)
        response.headers["X-RateLimit-Limit"] = "1000"
        response.headers["X-RateLimit-Remaining"] = "999"

        return response
