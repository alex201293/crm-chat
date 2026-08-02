"""
CRM-Chat Backend Application Entry Point.

Configures FastAPI application with middleware, routers, and lifecycle events.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from src.config.settings import get_settings
from src.modules.auth.api.routes.auth_router import router as auth_router
from src.modules.auth.api.routes.roles_router import router as roles_router
from src.modules.chat.api.routes.chat_router import router as chat_router
from src.modules.chat.api.routes.websocket_handler import router as ws_router
from src.modules.chat.api.routes.widget_router import router as widget_router
from src.modules.chat.api.routes.agents_router import router as agents_router
from src.modules.chat.api.routes.dashboard_router import router as dashboard_router
from src.modules.campaigns.api.campaigns_router import router as campaigns_router
from src.modules.channels.whatsapp.api.whatsapp_router import router as whatsapp_router
from src.modules.crm.api.routes.crm_router import router as crm_router
from src.modules.knowledge.api.routes.knowledge_router import router as knowledge_router
from src.shared.api.exceptions import register_exception_handlers
from src.shared.api.middleware.rate_limit import RateLimitMiddleware
from src.shared.api.middleware.tenant import TenantMiddleware
from src.shared.infrastructure.database.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle: startup and shutdown events."""
    # Startup
    settings = get_settings()
    app.state.settings = settings

    yield

    # Shutdown
    await engine.dispose()


def create_app() -> FastAPI:
    """Application factory pattern."""
    settings = get_settings()

    app = FastAPI(
        title="CRM-Chat API",
        description=(
            "AI-powered omnichannel CRM & Chat platform.\n\n"
            "## Authentication\n"
            "All endpoints (except /health, /ready, and webhook receivers) require a Bearer JWT token.\n"
            "Obtain tokens via `POST /api/v1/auth/login` or `POST /api/v1/auth/register`.\n\n"
            "## Rate Limiting\n"
            "- Unauthenticated: 100 requests/minute per IP\n"
            "- Authenticated: 1000 requests/minute per user\n"
            "- Login endpoint: 10 attempts/minute per IP\n\n"
            "## Multi-Tenancy\n"
            "Data is isolated per tenant. The tenant is resolved from the JWT claims "
            "or via the `X-Tenant-ID` header for API key authentication.\n\n"
            "## Versioning\n"
            "API is versioned via URL path (`/api/v1/`). Breaking changes will increment the version.\n\n"
            "## Widget API\n"
            "The `/api/v1/widget/` endpoints use `X-API-Key` header authentication "
            "instead of JWT (for public website embedding)."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/api/openapi.json",
        license_info={"name": "Proprietary", "url": "https://crmchat.io/terms"},
        contact={"name": "CRM Chat API Support", "email": "api@crmchat.io"},
        lifespan=lifespan,
        openapi_tags=[
            {"name": "System", "description": "Health checks and system status"},
            {"name": "Authentication", "description": "Login, register, JWT, MFA, OAuth"},
            {"name": "Roles & Permissions", "description": "RBAC management"},
            {"name": "Chat", "description": "Conversation and message management"},
            {"name": "WebSocket", "description": "Real-time messaging via WebSocket"},
            {"name": "Widget", "description": "Public API for the embeddable chat widget"},
            {"name": "Knowledge Base", "description": "RAG document management and search"},
            {"name": "CRM", "description": "Contacts, companies, deals, pipeline, tasks"},
            {"name": "WhatsApp", "description": "WhatsApp Business API integration"},
            {"name": "Campaigns", "description": "Multi-channel campaign management"},
            {"name": "Agent Panel", "description": "Agent queue, metrics, SLA, satisfaction"},
            {"name": "Dashboard", "description": "Analytics and reporting"},
        ],
    )

    # --- Middleware (order matters: last added = first executed) ---

    # Trusted hosts
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.app.APP_ALLOWED_HOSTS,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting
    app.add_middleware(RateLimitMiddleware)

    # Multi-tenant resolution
    app.add_middleware(TenantMiddleware)

    # --- Exception Handlers ---
    register_exception_handlers(app)

    # --- Routers ---
    _register_routers(app)

    return app


def _register_routers(app: FastAPI) -> None:
    """Register all module routers with their prefixes."""
    # Health check (no prefix)
    @app.get("/health", tags=["System"])
    async def health_check() -> dict[str, str]:
        return {"status": "healthy", "service": "crm-chat-api"}

    @app.get("/ready", tags=["System"])
    async def readiness_check() -> dict[str, str]:
        # Future: check DB, Redis, RabbitMQ connectivity
        return {"status": "ready"}

    # --- Module Routers ---

    # Authentication
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(roles_router, prefix="/api/v1/auth", tags=["Roles & Permissions"])

    # Chat
    app.include_router(chat_router, prefix="/api/v1/chat", tags=["Chat"])
    app.include_router(ws_router, tags=["WebSocket"])
    app.include_router(widget_router, prefix="/api/v1/widget", tags=["Widget"])

    # Knowledge Base
    app.include_router(knowledge_router, prefix="/api/v1/knowledge", tags=["Knowledge Base"])

    # CRM
    app.include_router(crm_router, prefix="/api/v1/crm", tags=["CRM"])

    # WhatsApp Business
    app.include_router(whatsapp_router, prefix="/api/v1/channels/whatsapp", tags=["WhatsApp"])

    # Campaigns
    app.include_router(campaigns_router, prefix="/api/v1/campaigns", tags=["Campaigns"])

    # Agent Panel & Dashboard
    app.include_router(agents_router, prefix="/api/v1/agents", tags=["Agent Panel"])
    app.include_router(dashboard_router, prefix="/api/v1/dashboard", tags=["Dashboard"])


# Application instance
app = create_app()
