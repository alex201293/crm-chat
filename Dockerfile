# =============================================================================
# CRM Chat - Single Container (Backend + Frontend)
# =============================================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
COPY frontend/next.config.mjs ./next.config.mjs
ENV NEXT_PUBLIC_API_URL=""
ENV NEXT_PUBLIC_WS_URL=""
ENV NEXT_PUBLIC_APP_NAME="CRM Chat"
RUN npm run build

# =============================================================================
FROM python:3.13-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl nginx supervisor nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY backend/pyproject.toml /app/backend/
WORKDIR /app/backend
RUN pip install --no-cache-dir \
    fastapi "uvicorn[standard]" pydantic pydantic-settings \
    "sqlalchemy[asyncio]" asyncpg alembic redis \
    "pyjwt[crypto]" bcrypt pyotp httpx \
    structlog python-slugify phonenumbers email-validator \
    python-multipart aiofiles tiktoken

# Copy backend code
COPY backend/src /app/backend/src
COPY backend/alembic /app/backend/alembic
COPY backend/alembic.ini /app/backend/

# Copy frontend build
COPY --from=frontend-builder /app/frontend/.next/standalone /app/frontend
COPY --from=frontend-builder /app/frontend/.next/static /app/frontend/.next/static
COPY --from=frontend-builder /app/frontend/public /app/frontend/public

# Storage
RUN mkdir -p /app/backend/storage/knowledge

# Nginx config
COPY infrastructure/nginx/single-container.conf /etc/nginx/nginx.conf

# Supervisor config
COPY infrastructure/docker/supervisord.conf /etc/supervisor/conf.d/app.conf

WORKDIR /app

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/app.conf"]
