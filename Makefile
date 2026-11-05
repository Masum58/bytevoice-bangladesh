.DEFAULT_GOAL := help

# Self-documenting help
.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

.PHONY: setup
setup: ## Install dependencies
	uv sync --all-groups

.PHONY: bytevoice-api
bytevoice-api: ## Launch ByteVoice FastAPI backend on :8000
	uvicorn main:app --reload --port 8000

.PHONY: bytevoice-agent
bytevoice-agent: ## Provision or update the ByteVoice Bangla agent on ElevenLabs
	uv run python scripts/setup_bytevoice_agent.py

.PHONY: web-build
web-build: ## Build the Next.js frontend into static export (web/out)
	cd web && npm ci && npm run build

.PHONY: web-dev
web-dev: ## Next.js dev server on :3000 against FastAPI on :8000
	cd web && npm run dev

.PHONY: docker-up
docker-up: ## Build and start ByteVoice with PostgreSQL in Docker
	docker compose up --build

.PHONY: docker-down
docker-down: ## Stop Docker containers
	docker compose down

.PHONY: test
test: ## Run the pytest test suite
	uv run pytest

.PHONY: lint
lint: ## Lint with ruff
	uv run ruff check .

.PHONY: format
format: ## Format with ruff
	uv run ruff format .
	uv run ruff check --fix .
