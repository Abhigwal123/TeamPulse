# Docker Quick Start Guide

Quick reference for deploying the Smart Scheduling System with Docker.

## 🚀 Quick Commands

### Initial Setup

```bash
# 1. Setup (first time only)
./scripts/setup.sh
# OR manually:
cp env.example .env
# Edit .env with your settings

# 2. Build and start
make up
# OR
docker-compose up -d --build

# 3. Initialize database
make init-db
# OR
docker-compose exec backend python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"
```

### Daily Operations

```bash
# Start services
make up

# Stop services
make down

# View logs
make logs

# Restart services
make restart

# Check status
make status
```

### Production Deployment

```bash
# Deploy to production
./scripts/deploy.sh production
# OR
make prod-up

# Stop production
make prod-down
```

## 📋 Service URLs

After starting services, access:

- **Frontend**: http://localhost
- **Backend API**: http://localhost:8000/api/v1
- **Health Check**: http://localhost:8000/api/v1/health
- **AI Service**: http://localhost:5001/health

## 🔧 Common Tasks

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
make logs-backend
make logs-frontend
make logs-celery
make logs-ai
```

### Database Operations

```bash
# Initialize database
make init-db

# Run migrations
make migrate

# Create migration
make migrate-create MESSAGE="description"

# Backup database
make backup
```

### Scaling

```bash
# Scale celery workers
WORKERS=3 make scale-worker
```

### Troubleshooting

```bash
# Check service health
make health

# Restart specific service
docker-compose restart backend

# Rebuild specific service
docker-compose build --no-cache backend
docker-compose up -d backend
```

## 📁 File Structure

```
Project_Up/
├── docker-compose.yml          # Main compose file
├── docker-compose.prod.yml     # Production overrides
├── Makefile                    # Convenience commands
├── scripts/
│   ├── setup.sh               # Initial setup
│   └── deploy.sh              # Deployment script
├── backend/
│   ├── Dockerfile             # Backend image
│   └── .dockerignore
├── frontend/
│   ├── Dockerfile             # Frontend image
│   ├── nginx.conf             # Nginx config
│   └── .dockerignore
└── ai_service/
    └── Dockerfile             # AI service image (already exists)
```

## 🐳 Docker Services

| Service | Port | Description |
|---------|------|-------------|
| frontend | 80 | React/Vite frontend (Nginx) |
| backend | 8000 | Flask API server |
| ai-service | 5001 | AI scheduling microservice |
| redis | 6379 | Redis cache & message broker |
| celery-worker | - | Async task processor |
| celery-beat | - | Periodic task scheduler |

## 🔐 Environment Variables

Required in `.env`:

```bash
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
DATABASE_URL=sqlite:///instance/scheduling_system.db
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

## 📚 More Information

- **Full Documentation**: See [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)
- **Setup Guide**: See [SETUP_GUIDE.md](SETUP_GUIDE.md)
- **API Documentation**: See [backend/API_DOCUMENTATION.md](backend/API_DOCUMENTATION.md)

---

**Quick Help**: Run `make help` to see all available commands.

