.PHONY: help install install-backend install-frontend run-backend run-frontend \
        test test-backend test-frontend lint typecheck build clean clean-db

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: install-backend install-frontend ## Install backend and frontend dependencies

install-backend: ## Install Python dependencies with uv
	uv sync

install-frontend: ## Install Node dependencies
	cd frontend && npm install

run-backend: ## Start the FastAPI backend on :8000
	uv run uvicorn backend.app.main:app --reload --port 8000

run-frontend: ## Start the Vite dev server on :5173
	cd frontend && npm run dev

test: test-backend test-frontend ## Run every test (backend + contract + frontend)

test-backend: ## Run pytest (API, business rules, stats, contract)
	uv run pytest

test-frontend: ## Run vitest (components, API client, formatting)
	cd frontend && npm run test

lint: ## Lint Python (ruff) and TypeScript (eslint)
	uv run ruff check .
	cd frontend && npm run lint

typecheck: ## Typecheck the frontend
	cd frontend && npm run typecheck

build: ## Production build of the frontend
	cd frontend && npm run build

clean-db: ## Delete the local SQLite database (demo data is reseeded on next start)
	rm -f tableturn.db

clean: clean-db ## Remove build artefacts and caches
	rm -rf frontend/dist frontend/coverage .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} +
