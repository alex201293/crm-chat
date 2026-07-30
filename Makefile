.PHONY: help dev stop build test lint migrate seed clean

# Default target
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development
dev: ## Start all services for local development
	docker compose up -d

stop: ## Stop all services
	docker compose down

restart: ## Restart all services
	docker compose down && docker compose up -d

logs: ## View logs from all services
	docker compose logs -f

logs-backend: ## View backend logs
	docker compose logs -f backend

# Build
build: ## Build all Docker images
	docker compose build

build-prod: ## Build production images
	docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# Database
migrate: ## Run database migrations
	docker compose exec backend alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MSG="description")
	docker compose exec backend alembic revision --autogenerate -m "$(MSG)"

migrate-rollback: ## Rollback last migration
	docker compose exec backend alembic downgrade -1

seed: ## Seed database with sample data
	docker compose exec backend python -m src.shared.infrastructure.database.seed

# Testing
test: ## Run all tests
	docker compose exec backend pytest

test-unit: ## Run unit tests only
	docker compose exec backend pytest tests/unit -v

test-integration: ## Run integration tests
	docker compose exec backend pytest tests/integration -v

test-coverage: ## Run tests with coverage report
	docker compose exec backend pytest --cov=src --cov-report=html --cov-report=term

# Linting
lint: ## Run linters
	docker compose exec backend ruff check src/ tests/
	docker compose exec backend mypy src/

lint-fix: ## Fix linting issues automatically
	docker compose exec backend ruff check --fix src/ tests/
	docker compose exec backend ruff format src/ tests/

# Frontend
frontend-dev: ## Start frontend in dev mode
	cd frontend && npm run dev

frontend-build: ## Build frontend for production
	cd frontend && npm run build

frontend-lint: ## Lint frontend code
	cd frontend && npm run lint

# Cleanup
clean: ## Remove all containers, volumes, and build artifacts
	docker compose down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true

# Utils
shell: ## Open a shell in the backend container
	docker compose exec backend bash

db-shell: ## Open PostgreSQL shell
	docker compose exec postgres psql -U postgres -d crm_chat

redis-shell: ## Open Redis CLI
	docker compose exec redis redis-cli
