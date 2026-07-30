# Despliegue en VPS

Guía completa para desplegar CRM Chat en un VPS (Ubuntu 22.04/24.04).

## Requisitos del VPS

- **OS:** Ubuntu 22.04+ o Debian 12+
- **RAM:** Mínimo 2GB (recomendado 4GB)
- **CPU:** 2 cores
- **Disco:** 20GB+
- **Dominio:** apuntando al IP del VPS (ej: app.tudominio.com)

---

## 1. Conectarse al VPS

```bash
ssh root@TU_IP_VPS
```

---

## 2. Instalar dependencias del sistema

```bash
# Actualizar
apt update && apt upgrade -y

# Instalar dependencias base
apt install -y git curl wget build-essential software-properties-common \
  nginx certbot python3-certbot-nginx \
  postgresql postgresql-contrib \
  redis-server \
  supervisor

# Instalar Python 3.13+
add-apt-repository ppa:deadsnakes/ppa -y
apt update
apt install -y python3.13 python3.13-venv python3.13-dev

# Instalar Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs
```

---

## 3. Configurar PostgreSQL

```bash
sudo -u postgres psql << 'EOF'
CREATE USER crmchat WITH PASSWORD 'TU_PASSWORD_SEGURO_AQUI';
CREATE DATABASE crm_chat OWNER crmchat;
\c crm_chat
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
\q
EOF
```

Para pgvector (RAG con embeddings):
```bash
apt install -y postgresql-16-pgvector
sudo -u postgres psql -d crm_chat -c 'CREATE EXTENSION IF NOT EXISTS vector;'
```

---

## 4. Configurar Redis

```bash
# Ya está corriendo por defecto
systemctl enable redis-server
systemctl start redis-server
```

---

## 5. Clonar el proyecto

```bash
mkdir -p /opt/crm-chat
cd /opt/crm-chat
git clone https://github.com/alex201293/crm-chat.git .
```

---

## 6. Configurar el Backend

```bash
cd /opt/crm-chat/backend

# Crear entorno virtual
python3.13 -m venv .venv
source .venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install fastapi "uvicorn[standard]" pydantic pydantic-settings \
  "sqlalchemy[asyncio]" asyncpg alembic redis \
  "pyjwt[crypto]" "passlib[bcrypt]" bcrypt pyotp httpx \
  structlog python-slugify phonenumbers email-validator \
  python-multipart aiofiles tiktoken

# Crear archivo .env
cat > .env << 'EOF'
APP_NAME=crm-chat
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=GENERA_UN_STRING_ALEATORIO_DE_64_CARACTERES
APP_ALLOWED_HOSTS=["app.tudominio.com","tudominio.com"]

BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
BACKEND_WORKERS=4
BACKEND_RELOAD=false

DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=crm_chat
DATABASE_USER=crmchat
DATABASE_PASSWORD=TU_PASSWORD_SEGURO_AQUI
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_ECHO=false

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

JWT_SECRET_KEY=GENERA_OTRO_STRING_ALEATORIO_DE_64_CARACTERES
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

GROQ_API_KEY=gsk_TU_KEY_DE_GROQ

STORAGE_DRIVER=local
STORAGE_PATH=/opt/crm-chat/backend/storage
EOF

# Crear directorio de storage
mkdir -p storage/knowledge

# Crear tablas
python -c "
import asyncio
from src.shared.infrastructure.database.base import Base
from src.shared.infrastructure.database.session import engine
from src.modules.auth.infrastructure.models import *
from src.modules.chat.infrastructure.models import *
from src.modules.crm.infrastructure.models import *
from src.modules.campaigns.infrastructure.repositories import CampaignModel, SegmentModel, CampaignMessageModel
from src.modules.knowledge.infrastructure.vectorstore.models import DocumentModel, FAQModel

async def create():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('Tables created')

asyncio.run(create())
"
```

---

## 7. Configurar el Frontend

```bash
cd /opt/crm-chat/frontend

# Instalar dependencias
npm install

# Crear .env.local
cat > .env.local << 'EOF'
NEXT_PUBLIC_API_URL=https://app.tudominio.com
NEXT_PUBLIC_WS_URL=wss://app.tudominio.com/ws
NEXT_PUBLIC_APP_NAME=CRM Chat
EOF

# Build de producción
npm run build
```

---

## 8. Configurar Supervisor (mantener procesos vivos)

```bash
cat > /etc/supervisor/conf.d/crm-chat-backend.conf << 'EOF'
[program:crm-chat-backend]
command=/opt/crm-chat/backend/.venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
directory=/opt/crm-chat/backend
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/crm-chat/backend.err.log
stdout_logfile=/var/log/crm-chat/backend.out.log
environment=PATH="/opt/crm-chat/backend/.venv/bin:%(ENV_PATH)s"
EOF

cat > /etc/supervisor/conf.d/crm-chat-frontend.conf << 'EOF'
[program:crm-chat-frontend]
command=/usr/bin/node /opt/crm-chat/frontend/.next/standalone/server.js
directory=/opt/crm-chat/frontend/.next/standalone
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/crm-chat/frontend.err.log
stdout_logfile=/var/log/crm-chat/frontend.out.log
environment=PORT="3001",HOSTNAME="0.0.0.0",NODE_ENV="production"
EOF

# Crear directorio de logs
mkdir -p /var/log/crm-chat
chown www-data:www-data /var/log/crm-chat

# Dar permisos
chown -R www-data:www-data /opt/crm-chat/backend/storage

# Recargar supervisor
supervisorctl reread
supervisorctl update
supervisorctl start all
```

---

## 9. Configurar Nginx + SSL

```bash
cat > /etc/nginx/sites-available/crm-chat << 'EOF'
server {
    listen 80;
    server_name app.tudominio.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name app.tudominio.com;

    # SSL (Certbot lo configura automáticamente)
    ssl_certificate /etc/letsencrypt/live/app.tudominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.tudominio.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Strict-Transport-Security "max-age=31536000" always;

    client_max_body_size 50m;

    # API Backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # Swagger docs
    location /docs {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }

    location /redoc {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000;
    }

    # Frontend (Next.js)
    location / {
        proxy_pass http://127.0.0.1:3001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Activar el sitio
ln -sf /etc/nginx/sites-available/crm-chat /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Probar configuración
nginx -t

# Obtener certificado SSL (primero sin SSL)
# Temporalmente cambia el server block a solo listen 80 sin redirect
certbot --nginx -d app.tudominio.com --non-interactive --agree-tos -m tu@email.com

# Reiniciar nginx
systemctl restart nginx
```

---

## 10. Verificar que todo funciona

```bash
# Ver status de los servicios
supervisorctl status

# Probar API
curl https://app.tudominio.com/health

# Ver logs si algo falla
tail -f /var/log/crm-chat/backend.err.log
tail -f /var/log/crm-chat/frontend.err.log
```

---

## 11. Crear usuario administrador

```bash
curl -X POST https://app.tudominio.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@tudominio.com",
    "password": "TuPasswordSeguro123!",
    "full_name": "Administrador",
    "company_name": "Tu Empresa"
  }'
```

---

## 12. Accesos finales

| Servicio | URL |
|----------|-----|
| **Frontend** | https://app.tudominio.com |
| **API Docs** | https://app.tudominio.com/docs |
| **Widget JS** | https://app.tudominio.com/api/v1/widget/ |
| **WebSocket** | wss://app.tudominio.com/ws |
| **WhatsApp Webhook** | https://app.tudominio.com/api/v1/channels/whatsapp/webhook |

---

## Comandos útiles

```bash
# Reiniciar backend
supervisorctl restart crm-chat-backend

# Reiniciar frontend
supervisorctl restart crm-chat-frontend

# Ver logs en vivo
tail -f /var/log/crm-chat/backend.out.log

# Actualizar código
cd /opt/crm-chat
git pull
cd backend && source .venv/bin/activate && pip install -r requirements.txt
cd ../frontend && npm install && npm run build
supervisorctl restart all
```

---

## Generar secrets seguros

```bash
# Para APP_SECRET_KEY y JWT_SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```
