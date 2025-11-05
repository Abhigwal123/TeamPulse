# 🚀 Quick Setup Guide

Complete setup instructions for the Smart Scheduling System - Frontend, Backend, Redis, and Celery.

---

## 📦 Prerequisites

- **Python 3.10+**
- **Node.js 18+** and npm
- **Docker** (for Redis) or install Redis locally
- **Google Service Account** credentials file

---

## 🔐 Step 1: Google Service Account Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable **Google Sheets API**
4. Create **Service Account**:
   - Go to "IAM & Admin" → "Service Accounts"
   - Create new service account
   - Download JSON credentials
5. Place credentials file in project root:
   ```
   Project_Up/
   └── service-account-creds.json
   ```
6. Share your Google Sheets with the service account email (found in the JSON file)

---

## 🔴 Step 2: Redis Setup

### Option A: Using Docker (Recommended)

```bash
# Start Redis container
docker run -d --name redis-scheduling -p 6379:6379 redis:7-alpine

# Verify it's running
docker exec -it redis-scheduling redis-cli ping
# Should return: PONG
```

### Option B: Local Installation

**Windows:**
- Download from [Redis for Windows](https://github.com/microsoftarchive/redis/releases)
- Run `redis-server.exe`

**Linux/Mac:**
```bash
sudo apt-get install redis-server  # Ubuntu/Debian
brew install redis                 # macOS
redis-server                       # Start server
```

---

## 🔧 Step 3: Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment (if not exists)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements_flask.txt
```

### Configure Environment

Create `.env` file in `backend/` directory (or copy from `env.example`):

```bash
# Database
DATABASE_URL=sqlite:///scheduling_system.db

# Redis/Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# JWT Secrets
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-change-in-production

# Google Sheets
GOOGLE_APPLICATION_CREDENTIALS=../service-account-creds.json

# CORS (comma-separated)
BACKEND_CORS_ORIGINS=http://localhost:5173,http://localhost:5174
```

### Initialize Database

```bash
cd backend
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"
```

### Start Backend Server

```bash
cd backend
python main.py
```

**Backend runs on:** `http://localhost:5000` (default) or `http://localhost:8000`

---

## ⚙️ Step 4: Celery Worker Setup

Open a **new terminal** (keep backend running):

```bash
cd backend

# Activate virtual environment
venv\Scripts\activate  # Windows
# OR
source venv/bin/activate  # Linux/Mac

# Start Celery worker
celery -A celery_worker.celery worker --loglevel=info

# Verify Celery is working
celery -A celery_worker.celery inspect registered
```

**Note:** Celery worker must be running for schedule execution tasks to work.

---

## 💻 Step 5: Frontend Setup

Open a **new terminal**:

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install
```

### Configure Environment

Create `.env` file in `frontend/` directory:

```bash
VITE_API_BASE_URL=http://localhost:5000/api/v1
# OR if backend runs on port 8000:
# VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### Start Frontend Development Server

```bash
cd frontend
npm run dev
```

**Frontend runs on:** `http://localhost:5173` (default)

---

## ✅ Step 6: Verify Everything is Running

### Check Services

1. **Redis**: `docker ps | grep redis` or `redis-cli ping`
2. **Backend**: Open `http://localhost:5000/api/v1/health` in browser
3. **Celery**: Should see "celery@hostname ready" in terminal
4. **Frontend**: Open `http://localhost:5173` in browser

### Test Endpoints

```bash
# Health check
curl http://localhost:5000/api/v1/health

# List all routes
curl http://localhost:5000/api/v1/routes
```

---

## 🎯 Quick Start Summary

**Open 4 terminals:**

**Terminal 1 - Redis:**
```bash
docker run -d --name redis-scheduling -p 6379:6379 redis:7-alpine
```

**Terminal 2 - Backend:**
```bash
cd backend
venv\Scripts\activate  # Windows
python main.py
```

**Terminal 3 - Celery:**
```bash
cd backend
venv\Scripts\activate  # Windows
celery -A celery_worker.celery worker --loglevel=info
```

**Terminal 4 - Frontend:**
```bash
cd frontend
npm run dev
```

---

## 🧪 Test Credentials

After setting up, you can create users via registration endpoint or use these test credentials (if seeded):

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | SysAdmin |
| `client_admin` | `client123` | ClientAdmin |
| `schedulemanager` | `manager123` | ScheduleManager |
| `employee` | `employee123` | Department_Employee |

---

## 🔍 Troubleshooting

### Redis Connection Failed
```bash
# Check Redis is running
docker ps | grep redis
# Restart if needed
docker restart redis-scheduling
```

### Celery Not Processing Tasks
```bash
# Check Redis connection
docker exec -it redis-scheduling redis-cli ping

# Check Celery worker
celery -A celery_worker.celery inspect active
```

### Backend Not Starting
```bash
# Check database exists
ls backend/instance/*.db

# Recreate database
cd backend
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"
```

### Google Sheets Not Working
- Verify `service-account-creds.json` exists in project root
- Check file path in `.env`: `GOOGLE_APPLICATION_CREDENTIALS=../service-account-creds.json`
- Ensure service account email has access to your Google Sheets

### Frontend Can't Connect to Backend
- Check `.env` file: `VITE_API_BASE_URL=http://localhost:5000/api/v1`
- Verify backend is running on correct port
- Check CORS settings in backend `config.py`

---

## 📝 Environment Files Structure

```
Project_Up/
├── service-account-creds.json    # Google Service Account (required)
├── backend/
│   └── .env                       # Backend configuration
└── frontend/
    └── .env                       # Frontend configuration
```

---

## 🔗 Default URLs

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:5000/api/v1
- **Health Check**: http://localhost:5000/api/v1/health
- **Routes List**: http://localhost:5000/api/v1/routes

---

**That's it! You're ready to go! 🎉**

