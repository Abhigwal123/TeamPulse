# Docker Deployment Guide

Complete guide for deploying the Smart Scheduling System using Docker and Docker Compose.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Building Images](#building-images)
- [Running with Docker Compose](#running-with-docker-compose)
- [Production Deployment](#production-deployment)
- [CI/CD Pipeline](#cicd-pipeline)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

- **Docker** 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- **Docker Compose** 2.0+ (included with Docker Desktop)
- **Git** (for cloning repository)

### Required Files

- `service-account-creds.json` - Google Service Account credentials
  - Place in project root directory
  - See [SETUP_GUIDE.md](SETUP_GUIDE.md) for instructions

---

## Quick Start

### 1. Clone Repository

```bash
git clone <repository-url>
cd Project_Up
```

### 2. Prepare Environment

```bash
# Copy environment example
cp env.example .env

# Edit .env with your configuration
nano .env
```

### 3. Start All Services

```bash
# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f
```

### 4. Initialize Database

```bash
# Initialize database
docker-compose exec backend python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"
```

### 5. Access Application

- **Frontend**: http://localhost
- **Backend API**: http://localhost:8000/api/v1
- **Health Check**: http://localhost:8000/api/v1/health
- **AI Service**: http://localhost:5001/health

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Application
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-change-in-production

# Database
DATABASE_URL=sqlite:///instance/scheduling_system.db

# Redis/Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Google Sheets
GOOGLE_APPLICATION_CREDENTIALS=/app/service-account-creds.json

# CORS
BACKEND_CORS_ORIGINS=http://localhost:80,http://localhost:5173
```

### Service Configuration

#### Backend

- **Port**: 8000
- **Environment**: Set via `FLASK_ENV` (default: production)
- **Database**: SQLite (stored in volume `backend_data`)

#### Frontend

- **Port**: 80
- **API URL**: Configured via `VITE_API_BASE_URL` build arg
- **Nginx**: Serves static files and proxies API requests

#### AI Service

- **Port**: 5001
- **Environment**: Production mode

#### Redis

- **Port**: 6379
- **Persistence**: Enabled with AOF (Append Only File)

---

## Building Images

### Build All Images

```bash
docker-compose build
```

### Build Specific Service

```bash
# Backend
docker-compose build backend

# Frontend
docker-compose build frontend

# AI Service
docker-compose build ai-service
```

### Build with Custom Arguments

```bash
# Frontend with custom API URL
docker-compose build --build-arg VITE_API_BASE_URL=https://api.example.com/api/v1 frontend
```

---

## Running with Docker Compose

### Start All Services

```bash
docker-compose up -d
```

### Start Specific Services

```bash
# Start only backend and Redis
docker-compose up -d redis backend

# Start frontend
docker-compose up -d frontend
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f celery-worker
docker-compose logs -f frontend
```

### Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ deletes data)
docker-compose down -v
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart backend
```

### Update Services

```bash
# Pull latest images and restart
docker-compose pull
docker-compose up -d
```

---

## Production Deployment

### Production Configuration

Use the production override file:

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Production Checklist

- [ ] Set strong `SECRET_KEY` and `JWT_SECRET_KEY`
- [ ] Configure `BACKEND_CORS_ORIGINS` with production URLs
- [ ] Use PostgreSQL or MySQL instead of SQLite
- [ ] Set up SSL/TLS certificates (use reverse proxy like Nginx)
- [ ] Configure backup strategy for databases
- [ ] Set up monitoring and logging
- [ ] Configure resource limits
- [ ] Set up health checks
- [ ] Configure firewall rules

### Using PostgreSQL (Production)

1. **Update docker-compose.yml:**

```yaml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: scheduling
      POSTGRES_USER: scheduler
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - scheduling-network

  backend:
    environment:
      - DATABASE_URL=postgresql://scheduler:${POSTGRES_PASSWORD}@postgres:5432/scheduling
    depends_on:
      - postgres
```

2. **Run migrations:**

```bash
docker-compose exec backend flask db upgrade
```

### Using Nginx as Reverse Proxy

Create `nginx/nginx.conf`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://frontend:80;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSL/TLS Setup

Use Let's Encrypt with Certbot:

```bash
# Add to docker-compose.yml
services:
  certbot:
    image: certbot/certbot
    volumes:
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
```

---

## CI/CD Pipeline

### GitHub Actions

The project includes a GitHub Actions workflow (`.github/workflows/ci-cd.yml`) that:

1. **Tests**: Runs backend and frontend tests
2. **Builds**: Builds Docker images
3. **Pushes**: Pushes images to GitHub Container Registry
4. **Deploys**: Deploys to production on main branch
5. **Scans**: Security scanning with Trivy

### Setup CI/CD

1. **Create GitHub Secrets:**

   - `PROD_HOST`: Production server hostname
   - `PROD_USER`: SSH username
   - `PROD_SSH_KEY`: SSH private key

2. **Configure Container Registry:**

   - Images are pushed to `ghcr.io/<username>/<repo-name>`
   - Authentication uses `GITHUB_TOKEN` (automatically provided)

3. **Manual Deployment:**

   ```bash
   # On production server
   docker login ghcr.io -u <username> -p <token>
   docker-compose pull
   docker-compose up -d
   ```

### GitLab CI/CD (Alternative)

Create `.gitlab-ci.yml`:

```yaml
stages:
  - build
  - test
  - deploy

build:
  stage: build
  script:
    - docker-compose build

test:
  stage: test
  script:
    - docker-compose run backend pytest
    - docker-compose run frontend npm test

deploy:
  stage: deploy
  script:
    - docker-compose up -d
  only:
    - main
```

---

## Monitoring & Maintenance

### Health Checks

```bash
# Check all services
docker-compose ps

# Check health status
curl http://localhost:8000/api/v1/health
curl http://localhost:5001/health
curl http://localhost/health
```

### Database Backup

```bash
# Backup SQLite database
docker-compose exec backend cp /app/instance/scheduling_system.db /app/instance/backup_$(date +%Y%m%d).db

# Backup volume
docker run --rm -v scheduling_backend_data:/data -v $(pwd):/backup alpine tar czf /backup/backend_backup.tar.gz /data
```

### Logs Management

```bash
# View logs
docker-compose logs --tail=100 -f

# Export logs
docker-compose logs > logs_$(date +%Y%m%d).txt

# Rotate logs (configure in docker-compose.yml)
```

### Resource Usage

```bash
# Check resource usage
docker stats

# Check disk usage
docker system df
```

---

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose logs

# Check service status
docker-compose ps

# Restart services
docker-compose restart
```

### Database Issues

```bash
# Recreate database
docker-compose down -v
docker-compose up -d
docker-compose exec backend python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"
```

### Redis Connection Issues

```bash
# Check Redis
docker-compose exec redis redis-cli ping

# Restart Redis
docker-compose restart redis
```

### Celery Worker Not Processing

```bash
# Check Celery worker
docker-compose logs celery-worker

# Restart worker
docker-compose restart celery-worker

# Check active tasks
docker-compose exec celery-worker celery -A celery_worker.celery inspect active
```

### Frontend Not Loading

```bash
# Check frontend logs
docker-compose logs frontend

# Check nginx configuration
docker-compose exec frontend nginx -t

# Rebuild frontend
docker-compose build --no-cache frontend
docker-compose up -d frontend
```

### Port Already in Use

```bash
# Change ports in docker-compose.yml
services:
  backend:
    ports:
      - "8001:8000"  # Change 8000 to 8001
```

### Permission Issues

```bash
# Fix permissions
sudo chown -R $USER:$USER .
docker-compose down
docker-compose up -d
```

---

## Scaling

### Horizontal Scaling

```bash
# Scale celery workers
docker-compose up -d --scale celery-worker=3

# Scale backend (requires load balancer)
docker-compose up -d --scale backend=3
```

### Resource Limits

Configure in `docker-compose.prod.yml`:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

---

## Security Best Practices

1. **Use Secrets Management:**
   ```bash
   docker secret create secret_key ./secret_key.txt
   ```

2. **Run as Non-Root:**
   - All containers run as non-root users

3. **Network Isolation:**
   - Services communicate via internal network

4. **Regular Updates:**
   ```bash
   docker-compose pull
   docker-compose up -d
   ```

5. **Scan for Vulnerabilities:**
   ```bash
   docker scan <image-name>
   ```

---

## Backup & Recovery

### Backup Script

Create `scripts/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
docker-compose exec -T backend python -c "from app import create_app; import shutil; shutil.copy('instance/scheduling_system.db', f'/tmp/backup_{$DATE}.db')"
docker cp scheduling-backend:/tmp/backup_$DATE.db $BACKUP_DIR/

# Backup volumes
docker run --rm -v scheduling_backend_data:/data -v $(pwd)/$BACKUP_DIR:/backup alpine tar czf /backup/backend_$DATE.tar.gz /data

echo "Backup completed: $BACKUP_DIR"
```

### Recovery

```bash
# Restore database
docker cp backups/backup_20250101.db scheduling-backend:/app/instance/scheduling_system.db
docker-compose restart backend

# Restore volume
docker run --rm -v scheduling_backend_data:/data -v $(pwd)/backups:/backup alpine tar xzf /backup/backend_20250101.tar.gz -C /
```

---

## Support

For issues or questions:
1. Check logs: `docker-compose logs`
2. Review troubleshooting section
3. Check GitHub issues
4. Consult SETUP_GUIDE.md for manual setup

---

**Happy Deploying! 🚀**

