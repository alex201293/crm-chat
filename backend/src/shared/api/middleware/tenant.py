"""
Tenant resolution middleware.
Resolves the current tenant from the request context (header, subdomain, or JWT).
Sets tenant context for downstream request processing.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


# Paths that don't require tenant context
TENANT_EXEMPT_PATHS = frozenset({
    "/health",
    "/ready",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
})

# Path prefixes exempt from tenant resolution
TENANT_EXEMPT_PREFIXES = (
    "/docs",
    "/redoc",
)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Resolves tenant from request context.

    Resolution order:
    1. X-Tenant-ID header (for API clients)
    2. Subdomain (tenant.app.com)
    3. JWT claims (for authenticated requests)

    Sets request.state.tenant_id for downstream use.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip tenant resolution for exempt paths
        path = request.url.path
        if path in TENANT_EXEMPT_PATHS or path.startswith(TENANT_EXEMPT_PREFIXES):
            request.state.tenant_id = None
            return await call_next(request)

        # Attempt to resolve tenant
        tenant_id = self._resolve_tenant(request)
        request.state.tenant_id = tenant_id

        return await call_next(request)

    def _resolve_tenant(self, request: Request) -> str | None:
        """
        Resolve tenant ID from available request information.
        Returns None if no tenant can be determined (handled by route-level auth).
        """
        # 1. Explicit header
        tenant_header = request.headers.get("X-Tenant-ID")
        if tenant_header:
            return tenant_header

        # 2. Subdomain resolution
        host = request.headers.get("host", "")
        parts = host.split(".")
        if len(parts) > 2:
            subdomain = parts[0]
            if subdomain not in ("www", "api", "app"):
                return subdomain

        # 3. Will be resolved from JWT in auth dependency
        return None
