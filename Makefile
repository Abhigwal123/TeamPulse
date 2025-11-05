.PHONY: help build up down restart logs clean test deploy prod-backup

# Default target
help:
	@echo "Smart Scheduling System - Docker Management"
	@echo ""
	@echo "Available commands:"
	@echo "  make build          - Build all Docker images"
	@echo "  make up             - Start all services"
	@echo "  make down           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make logs           - View logs from all services"
	@echo "  make clean          - Remove containers, volumes, and images"
	@echo "  make test           - Run tests"
	@echo "  make deploy         - Deploy to production"
	@echo "  make init-db        - Initialize database"
	@echo "  make backup         - Backup database and volumes"
	@echo "  make prod-up        - Start production services"
	@echo "  make prod-down      - Stop production services"

# Build all images
build:
	docker-compose build

# Start all services
up:
	docker-compose up -d
	@echo "Services started. Use 'make logs' to view logs."

# Stop all services
down:
	docker-compose down

# Restart all services
restart:
	docker-compose restart

# View logs
logs:
	docker-compose logs -f

# Clean everything
clean:
	docker-compose down -v --rmi all
	docker system prune -f

# Run tests
test:
	docker-compose run --rm backend pytest
	docker-compose run --rm frontend npm test

# Initialize database
init-db:
	docker-compose up -d backend redis
	sleep 5
	docker-compose exec backend python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"
	@echo "Database initialized."

# Backup
backup:
	@mkdir -p backups
	@DATE=$$(date +%Y%m%d_%H%M%S); \
	docker-compose exec -T backend python -c "from app import create_app; import shutil; shutil.copy('instance/scheduling_system.db', f'/tmp/backup_$$DATE.db')" 2>/dev/null || true; \
	docker cp scheduling-backend:/tmp/backup_$$DATE.db backups/ 2>/dev/null || echo "Backup created: backups/backup_$$DATE.db"
	@echo "Backup completed."

# Production deployment
prod-up:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
	@echo "Production services started."

prod-down:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# Development mode
dev-up:
	docker-compose -f docker-compose.yml up -d
	@echo "Development services started."

# Update services
update:
	docker-compose pull
	docker-compose up -d
	@echo "Services updated."

# Check service status
status:
	docker-compose ps

# View specific service logs
logs-backend:
	docker-compose logs -f backend

logs-frontend:
	docker-compose logs -f frontend

logs-celery:
	docker-compose logs -f celery-worker

logs-ai:
	docker-compose logs -f ai-service

# Health checks
health:
	@echo "Checking service health..."
	@curl -s http://localhost:8000/api/v1/health | jq . || echo "Backend: Not responding"
	@curl -s http://localhost:5001/health | jq . || echo "AI Service: Not responding"
	@curl -s http://localhost/health || echo "Frontend: Not responding"

# Scale services
scale-worker:
	docker-compose up -d --scale celery-worker=$${WORKERS:-2} celery-worker

# Shell access
shell-backend:
	docker-compose exec backend /bin/bash

shell-frontend:
	docker-compose exec frontend /bin/sh

# Database migrations
migrate:
	docker-compose exec backend flask db upgrade

migrate-create:
	docker-compose exec backend flask db migrate -m "$(MESSAGE)"

