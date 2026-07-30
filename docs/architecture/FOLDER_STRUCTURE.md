# Estructura del Monorepo

```
crm-chat/
├── backend/                          # Servidor principal (Python/FastAPI)
│   ├── alembic/                      # Migraciones de base de datos
│   │   ├── versions/                 # Archivos de migración versionados
│   │   ├── env.py                    # Configuración Alembic
│   │   └── alembic.ini              # Config principal Alembic
│   ├── src/
│   │   ├── config/                   # Configuración de la aplicación
│   │   │   ├── __init__.py
│   │   │   └── settings.py          # Variables de entorno, settings por ambiente
│   │   ├── shared/                   # Shared Kernel (código compartido entre módulos)
│   │   │   ├── domain/
│   │   │   │   ├── base_entity.py   # Entidad base con id, timestamps, tenant_id
│   │   │   │   ├── events.py        # Domain Event base, Event Bus interface
│   │   │   │   └── value_objects.py # Value Objects compartidos (Email, PhoneNumber, etc.)
│   │   │   ├── api/
│   │   │   │   ├── middleware/      # Rate limiting, CORS, tenant resolution, logging
│   │   │   │   ├── dependencies.py  # FastAPI dependencies compartidas
│   │   │   │   └── exceptions.py   # Exception handlers globales
│   │   │   └── infrastructure/
│   │   │       ├── database/
│   │   │       │   ├── base.py      # SQLAlchemy Base declarativa
│   │   │       │   └── session.py   # Async session factory, connection pool
│   │   │       ├── cache/           # Redis client, cache decorators
│   │   │       ├── messaging/       # RabbitMQ publisher/consumer
│   │   │       └── security/        # JWT, hashing, encryption utilities
│   │   └── modules/                  # Bounded Contexts (un módulo por dominio)
│   │       ├── auth/                 # Autenticación y Autorización
│   │       │   ├── api/
│   │       │   │   ├── routes/      # Endpoints: login, register, mfa, oauth
│   │       │   │   ├── schemas/     # Pydantic schemas (request/response)
│   │       │   │   └── dependencies/# Auth dependencies (current_user, permissions)
│   │       │   ├── application/
│   │       │   │   ├── commands/    # RegisterUser, LoginUser, ResetPassword
│   │       │   │   ├── queries/     # GetUser, ListUsers, GetPermissions
│   │       │   │   └── dtos/        # Data Transfer Objects
│   │       │   ├── domain/
│   │       │   │   ├── entities/    # User, Role, Permission, Tenant
│   │       │   │   ├── value_objects/# Email, HashedPassword, RefreshToken
│   │       │   │   ├── interfaces/ # IUserRepository, ITokenService
│   │       │   │   └── events/      # UserRegistered, PasswordChanged
│   │       │   └── infrastructure/
│   │       │       ├── repositories/# SQLAlchemy implementations
│   │       │       └── services/    # JWT service, OAuth providers, MFA
│   │       ├── chat/                 # Conversaciones en tiempo real
│   │       │   ├── api/
│   │       │   │   ├── routes/      # WebSocket handlers, REST endpoints
│   │       │   │   ├── schemas/
│   │       │   │   └── dependencies/
│   │       │   ├── application/
│   │       │   │   ├── commands/    # SendMessage, TransferToAgent, CloseConversation
│   │       │   │   ├── queries/     # GetConversations, GetMessages, GetMetrics
│   │       │   │   └── dtos/
│   │       │   ├── domain/
│   │       │   │   ├── entities/    # Conversation, Message, Participant
│   │       │   │   ├── value_objects/# MessageContent, ConversationStatus
│   │       │   │   ├── interfaces/ # IConversationRepository, IMessageBroker
│   │       │   │   └── events/      # MessageSent, ConversationEscalated
│   │       │   └── infrastructure/
│   │       │       ├── repositories/
│   │       │       └── services/    # WebSocket manager, presence tracking
│   │       ├── crm/                  # Gestión de relaciones con clientes
│   │       │   ├── api/routes/
│   │       │   ├── application/
│   │       │   │   ├── commands/    # CreateContact, UpdateDeal, MoveStage
│   │       │   │   └── queries/     # GetPipeline, GetContacts, GetActivities
│   │       │   ├── domain/
│   │       │   │   ├── entities/    # Contact, Company, Deal, Pipeline, Stage, Task
│   │       │   │   ├── interfaces/
│   │       │   │   └── events/      # DealStageChanged, ContactCreated
│   │       │   └── infrastructure/repositories/
│   │       ├── campaigns/            # Campañas multicanal
│   │       │   ├── api/routes/
│   │       │   ├── application/commands/ # CreateCampaign, SendCampaign, ScheduleCampaign
│   │       │   ├── domain/
│   │       │   │   ├── entities/    # Campaign, Segment, Template, CampaignMetrics
│   │       │   │   ├── interfaces/
│   │       │   │   └── events/      # CampaignSent, CampaignCompleted
│   │       │   └── infrastructure/repositories/
│   │       ├── channels/             # Integraciones con canales
│   │       │   ├── whatsapp/        # WhatsApp Business API
│   │       │   │   ├── api/         # Webhooks, endpoints
│   │       │   │   ├── domain/      # Templates, MediaMessage
│   │       │   │   └── infrastructure/ # Meta API client
│   │       │   ├── email/           # SMTP, SendGrid, AWS SES
│   │       │   ├── sms/            # Twilio, MessageBird
│   │       │   ├── telegram/       # Telegram Bot API
│   │       │   ├── facebook/       # Messenger API
│   │       │   └── instagram/      # Instagram Messaging
│   │       ├── ai/                   # Capa de abstracción IA
│   │       │   ├── application/services/ # AIService, PromptBuilder, ResponseEvaluator
│   │       │   ├── domain/interfaces/   # ILLMProvider, IEmbeddingProvider
│   │       │   └── infrastructure/providers/ # OpenAI, Claude, Gemini, Llama, Mistral
│   │       └── knowledge/           # Base de conocimiento (RAG)
│   │           ├── api/routes/      # Upload, search, manage documents
│   │           ├── application/commands/ # IndexDocument, ProcessUpload, SyncWebPage
│   │           ├── domain/
│   │           │   ├── entities/    # Document, Chunk, Embedding, FAQ
│   │           │   └── interfaces/ # IVectorStore, IDocumentParser
│   │           └── infrastructure/
│   │               ├── parsers/     # PDF, Word, Excel, TXT, HTML parsers
│   │               └── vectorstore/ # pgvector implementation
│   ├── tests/
│   │   ├── unit/                    # Tests unitarios por módulo
│   │   ├── integration/            # Tests de integración (DB, Redis, APIs)
│   │   └── e2e/                     # Tests end-to-end
│   ├── pyproject.toml               # Dependencias y configuración del proyecto
│   ├── Dockerfile                   # Multi-stage build para producción
│   └── .env.example                 # Variables de entorno de ejemplo
│
├── frontend/                         # Panel de administración (Next.js)
│   ├── src/
│   │   ├── app/                     # App Router de Next.js
│   │   │   ├── (auth)/             # Grupo de rutas: login, register, forgot-password
│   │   │   │   └── login/page.tsx
│   │   │   └── (dashboard)/        # Grupo de rutas: panel principal (requiere auth)
│   │   │       ├── layout.tsx       # Layout con sidebar, header
│   │   │       ├── chat/page.tsx    # Panel de agentes / conversaciones
│   │   │       ├── crm/page.tsx     # CRM / Pipeline
│   │   │       └── campaigns/page.tsx # Campañas
│   │   ├── components/
│   │   │   ├── ui/                  # Componentes base (Button, Input, Modal, etc.)
│   │   │   ├── chat/               # Componentes del chat (MessageList, ChatInput)
│   │   │   └── crm/                # Componentes del CRM (Pipeline, ContactCard)
│   │   ├── hooks/                   # Custom hooks
│   │   │   ├── use-auth.ts         # Autenticación
│   │   │   └── use-chat.ts         # WebSocket chat
│   │   ├── stores/                  # Estado global (Zustand)
│   │   │   ├── auth.store.ts
│   │   │   └── chat.store.ts
│   │   ├── lib/
│   │   │   ├── api/client.ts       # Axios/fetch configurado con interceptors
│   │   │   └── websocket/client.ts # WebSocket client con reconexión
│   │   └── types/index.ts          # TypeScript types compartidos
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── next.config.ts
│   └── Dockerfile
│
├── mobile/                           # App móvil (Flutter)
│   └── lib/src/
│       ├── core/
│       │   ├── api/                 # HTTP client, interceptors
│       │   ├── di/                  # Dependency injection (get_it/riverpod)
│       │   └── theme/               # Material Theme, colores, tipografía
│       └── features/
│           ├── auth/                # Login, registro
│           ├── chat/                # Conversaciones en tiempo real
│           └── crm/                 # CRM móvil
│
├── widget/                           # Widget embebible (TypeScript puro)
│   └── src/
│       ├── components/              # UI components (ChatWindow, MessageBubble)
│       ├── core/                    # WebSocket, API client, state management
│       └── styles/                  # CSS-in-JS o Shadow DOM styles
│
├── plugins/                          # Plugins para plataformas de ecommerce
│   ├── wordpress/                   # Plugin WordPress/WooCommerce
│   │   └── assets/
│   ├── woocommerce/                 # Extensión específica WooCommerce
│   ├── prestashop/
│   │   └── views/
│   ├── shopify/                     # Shopify App
│   │   └── assets/
│   └── magento/                     # Módulo Magento 2
│       └── etc/
│
├── infrastructure/                   # DevOps y configuración de infraestructura
│   ├── docker/                      # Dockerfiles adicionales (nginx, workers)
│   ├── k8s/                         # Kubernetes manifests
│   │   ├── base/                    # Base resources (deployments, services)
│   │   └── overlays/               # Kustomize overlays
│   │       ├── staging/
│   │       └── production/
│   └── nginx/
│       └── nginx.conf               # Reverse proxy configuration
│
├── docs/                             # Documentación del proyecto
│   └── architecture/
│       ├── ARCHITECTURE.md          # Documento principal de arquitectura
│       ├── FOLDER_STRUCTURE.md      # Este archivo
│       └── decisions/               # Architecture Decision Records (ADR)
│
├── docker-compose.yml               # Orquestación local de desarrollo
├── docker-compose.prod.yml          # Orquestación de producción
├── Makefile                          # Comandos de desarrollo simplificados
├── .gitignore
├── .env.example
└── .github/
    └── workflows/                   # CI/CD pipelines
```

## Convenciones

### Backend
- **Un módulo = Un bounded context**: Cada módulo es autónomo y puede extraerse como microservicio
- **Capas estrictas**: api/ → application/ → domain/ → infrastructure/
- **Domain nunca importa de infrastructure**: Las interfaces se definen en domain/, se implementan en infrastructure/
- **Shared kernel mínimo**: Solo código genuinamente transversal (base entities, security, database)

### Frontend
- **App Router groups**: (auth) y (dashboard) para separar layouts y protección de rutas
- **Colocación**: Components cerca de donde se usan, shared en components/ui/
- **Stores atómicos**: Un store por dominio, no un store monolítico

### Nomenclatura
- Backend: snake_case (Python)
- Frontend: camelCase para variables, PascalCase para componentes
- Archivos backend: snake_case.py
- Archivos frontend: kebab-case.ts/tsx
- Módulos: singular (auth, chat, crm) excepto cuando el plural es más natural (campaigns, channels)
