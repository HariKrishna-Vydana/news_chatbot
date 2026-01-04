.PHONY: install sync setup dev up down restart build logs clean status health rebuild-all fix-webrtc

# Installation
install:
	cd chat_backend && uv sync
	cd voice_backend && uv sync
	cd web_client && npm install

sync:
	cd chat_backend && uv sync --frozen
	cd voice_backend && uv sync --frozen

setup: install
	@test -f .env || cp .env.sample .env
	@test -f chat_backend/.env || cp chat_backend/.env.sample chat_backend/.env
	@test -f voice_backend/.env || cp voice_backend/.env.sample voice_backend/.env
	@test -f web_client/.env || cp web_client/.env.sample web_client/.env
	@echo "✓ Environment files created. Please edit .env files with your API keys."

# Development
dev:
	docker compose -f docker-compose.dev.yaml up --build

dev-rebuild:
	docker compose -f docker-compose.dev.yaml up --build --no-cache

dev-d:
	docker compose -f docker-compose.dev.yaml up --build -d

# Production
up:
	docker compose up --build -d

down:
	docker compose down

restart:
	docker compose restart

# Building
build:
	docker compose build --parallel

rebuild-all:
	docker compose build --parallel --no-cache

build-chat:
	docker compose build chat_backend --no-cache

build-voice:
	docker compose build voice_backend --no-cache

build-web:
	docker compose build web_client --no-cache

# Shell access
shell-chat:
	docker compose exec chat_backend /bin/bash

shell-voice:
	docker compose exec voice_backend /bin/bash

shell-web:
	docker compose exec web_client /bin/sh

# Logs
logs:
	docker compose logs -f

logs-chat:
	docker compose logs -f chat_backend

logs-voice:
	docker compose logs -f voice_backend

logs-web:
	docker compose logs -f web_client

# Status and Health
status:
	@echo "=== Container Status ==="
	@docker compose ps
	@echo "\n=== Service Health ==="
	@make --no-print-directory health

health:
	@echo -n "Chat Backend:  "
	@curl -sf http://localhost:8000/api/health > /dev/null && echo "✓ Healthy" || echo "✗ Unhealthy"
	@echo -n "Voice Backend: "
	@curl -sf http://localhost:7860/health > /dev/null && echo "✓ Healthy" || echo "✗ Unhealthy"
	@echo -n "Web Client:    "
	@curl -sf http://localhost > /dev/null && echo "✓ Healthy" || echo "✗ Unhealthy"

test-chat:
	curl -f http://localhost:8000/api/health || echo "Chat backend not healthy"

test-voice:
	curl -f http://localhost:7860/health || echo "Voice backend not healthy"

# Quick fixes
fix-webrtc:
	@echo "Rebuilding web_client and voice_backend to fix WebRTC issues..."
	docker compose stop web_client voice_backend
	docker compose rm -f web_client voice_backend
	docker compose build --no-cache web_client voice_backend
	docker compose up -d
	@echo "✓ Done! Test the connection at http://localhost"

fix-cache:
	@echo "Clearing Docker build cache and rebuilding..."
	docker builder prune -f
	make rebuild-all
	docker compose up -d
	@echo "✓ Done!"

# Cleanup
clean:
	docker compose down -v --remove-orphans
	docker system prune -f

clean-all: clean
	docker builder prune -af
	rm -rf chat_backend/.venv voice_backend/.venv web_client/node_modules
	@echo "✓ Complete cleanup done!"

# Help
help:
	@echo "News Chatbot - Available Commands"
	@echo "=================================="
	@echo ""
	@echo "Setup:"
	@echo "  make setup         - Initialize project and create .env files"
	@echo "  make install       - Install dependencies locally"
	@echo ""
	@echo "Running:"
	@echo "  make up            - Start all services (production)"
	@echo "  make down          - Stop all services"
	@echo "  make restart       - Restart all services"
	@echo "  make dev           - Run in development mode"
	@echo ""
	@echo "Building:"
	@echo "  make build         - Build all services"
	@echo "  make rebuild-all   - Force rebuild all (no cache)"
	@echo "  make build-web     - Rebuild just web client"
	@echo "  make build-voice   - Rebuild just voice backend"
	@echo "  make build-chat    - Rebuild just chat backend"
	@echo ""
	@echo "Monitoring:"
	@echo "  make status        - Show container status and health"
	@echo "  make health        - Check health of all services"
	@echo "  make logs          - Follow all logs"
	@echo "  make logs-voice    - Follow voice backend logs"
	@echo ""
	@echo "Troubleshooting:"
	@echo "  make fix-webrtc    - Fix WebRTC connection issues"
	@echo "  make fix-cache     - Clear build cache and rebuild"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean         - Stop and remove containers"
	@echo "  make clean-all     - Complete cleanup (containers + deps)"
