# Story R Us local DX — backend stack via backend/docker-compose.yml;
# Vite web runs on the host (proxy /v1 → :8000). No MinIO.
#
# Cloud Agent / broken Docker bridge: make up HOST_GATEWAY=1
COMPOSE_FILES := -f backend/docker-compose.yml
ifeq ($(HOST_GATEWAY),1)
COMPOSE_FILES += -f backend/docker-compose.host-gateway.yml
endif
COMPOSE := docker compose $(COMPOSE_FILES)
BACKEND_ENV := backend/.env
API_URL ?= http://localhost:8000

.PHONY: help init up down logs ps seed demo web restart kling-meupai

help: ## List targets
	@awk 'BEGIN {FS = ":.*##"; printf "Story R Us local DX\n\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  make %-10s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

init: ## Copy backend/.env.example → backend/.env if missing
	@if [ ! -f $(BACKEND_ENV) ]; then \
		cp backend/.env.example $(BACKEND_ENV); \
		echo "Created $(BACKEND_ENV) — fill AI/storage keys when you need real generation."; \
	else \
		echo "$(BACKEND_ENV) already exists."; \
	fi

up: init ## Build & start Postgres + Redis + API + worker
	$(COMPOSE) up --build -d
	@echo "API docs: http://localhost:8000/docs"
	@echo "Web (separate): make web  →  http://localhost:5173  (proxy /v1 → :8000)"

down: ## Stop backend compose stack
	$(COMPOSE) down

restart: ## Restart api + worker
	$(COMPOSE) up --build -d --force-recreate api worker

logs: ## Tail compose logs
	$(COMPOSE) logs -f

ps: ## Compose service status
	$(COMPOSE) ps

seed: init ## Seed demo user (demo@storyrus.app / demo12345)
	$(COMPOSE) run --rm api python scripts/seed.py

demo: ## Exercise API flow against running stack (needs make up)
	$(COMPOSE) run --rm -e API_URL=http://api:8000 api python scripts/demo_flow.py

web: ## Run Vite web on host (API must already be up)
	cd apps/web && npm install && npm run dev

kling-meupai: ## Animate Meu Pai pages with Kling (needs KLING_API_KEY in backend/.env)
	cd backend && .venv/bin/python scripts/gen_meupai_kling.py $(ARGS)
