# AI Scheduling Service - Documentation

## Overview

The AI Scheduling Service is a Flask-based microservice that provides intelligent task scheduling capabilities. It uses a deterministic scheduling algorithm to assign tasks to employees based on constraints, availability, skills, and workload balancing.

**Service Type:** Microservice (Flask REST API)  
**Port:** 5001  
**Language:** Python 3.9+  
**Framework:** Flask 2.3.3

---

## Table of Contents

- [Architecture](#architecture)
- [Features](#features)
- [API Endpoints](#api-endpoints)
- [Data Models](#data-models)
- [Scheduling Algorithm](#scheduling-algorithm)
- [Installation & Setup](#installation--setup)
- [Usage Examples](#usage-examples)
- [Deployment](#deployment)
- [Error Handling](#error-handling)
- [Limitations & Future Improvements](#limitations--future-improvements)

---

## Architecture

### Component Structure

```
ai_service/
├── app.py              # Main Flask application and scheduling logic
├── Dockerfile          # Docker container configuration
├── requirements.txt    # Python dependencies
└── README.md          # This documentation
```

### Service Architecture

```
┌─────────────────┐
│  Main Backend   │
│   (Flask App)   │
└────────┬────────┘
         │ HTTP POST
         │ /api/schedule/compute
         ▼
┌─────────────────┐
│  AI Service     │
│  (Port 5001)    │
└────────┬────────┘
         │
         ├──► DeterministicScheduler
         │    ├── Employee Management
         │    ├── Task Management
         │    └── Scheduling Algorithm
         │
         └──► Background Thread Processing
              └── Job Status Tracking
```

### Job Processing Flow

1. **Job Submission**: Client sends scheduling request to `/api/schedule/compute`
2. **Job Queuing**: Job is queued with status `queued`
3. **Background Processing**: Job processed in background thread
4. **Status Updates**: Job status updated to `in_progress` → `completed` or `failed`
5. **Result Retrieval**: Client polls `/api/schedule/result/<job_id>` for results

---

## Features

### Core Features

1. **Deterministic Scheduling**: Algorithm that respects hard constraints
2. **Employee-Task Matching**: Matches employees to tasks based on:
   - Department compatibility
   - Required skills
   - Availability windows
   - Current workload
3. **Workload Balancing**: Distributes tasks to balance employee workload
4. **Priority-Based Scheduling**: Tasks scheduled by priority and deadline
5. **Asynchronous Processing**: Jobs processed in background threads
6. **Job Status Tracking**: Real-time job status monitoring

### Supported Constraints

- Employee availability (time slots)
- Department matching
- Skill requirements
- Maximum hours per week
- Task dependencies (structure exists, not fully implemented)
- Task deadlines
- Task priority

---

## API Endpoints

### Base URL

- **Development**: `http://localhost:5001`
- **Production**: Configure via environment variables

### Endpoints

#### 1. POST /api/schedule/compute

Start a scheduling computation job.

**Request Body:**
```json
{
  "job_id": "string (required, unique identifier)",
  "tenant_id": "string (required)",
  "preschedule_data": [
    ["employee_id", "name", "department", "skills", "availability", "max_hours"],
    ["EMP001", "John Doe", "Sales", "communication,negotiation", "monday:09:00-17:00", "40"],
    ["EMP002", "Jane Smith", "IT", "python,javascript", "tuesday:09:00-17:00", "40"]
  ],
  "parameters": {
    "task_count": 10,
    "departments": ["Sales", "IT"],
    "date_range": "2025-01-01 to 2025-01-07",
    "task_duration_hours": 8,
    "task_priority": 1
  }
}
```

**Response (202 Accepted):**
```json
{
  "job_id": "job-123",
  "status": "queued",
  "message": "Scheduling job queued successfully"
}
```

**Error Responses:**
- `400`: Missing required fields (`job_id` or `tenant_id`)
- `500`: Internal server error

**Example:**
```bash
curl -X POST http://localhost:5001/api/schedule/compute \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "job-123",
    "tenant_id": "tenant-1",
    "preschedule_data": [
      ["ID", "Name", "Department", "Skills", "Availability", "Max Hours"],
      ["EMP001", "John Doe", "Sales", "communication", "monday:09:00-17:00", "40"]
    ],
    "parameters": {
      "task_count": 5,
      "departments": ["Sales"],
      "date_range": "2025-01-01 to 2025-01-07"
    }
  }'
```

---

#### 2. GET /api/schedule/result/<job_id>

Get the complete scheduling result for a job.

**Path Parameters:**
- `job_id`: String (required) - Job identifier

**Response (200 OK):**
```json
{
  "job_id": "job-123",
  "status": "completed",
  "started_at": "2025-01-01T10:00:00",
  "completed_at": "2025-01-01T10:05:00",
  "result_data": [
    {
      "task_id": "uuid-1",
      "employee_id": "EMP001",
      "employee_name": "John Doe",
      "start_time": "2025-01-01T09:00:00",
      "end_time": "2025-01-01T17:00:00",
      "department": "Sales",
      "status": "scheduled",
      "duration_hours": 8.0
    }
  ],
  "summary": {
    "total_tasks": 10,
    "scheduled_tasks": 8,
    "total_employees": 5,
    "utilization_rate": 0.8
  }
}
```

**Response (404 Not Found):**
```json
{
  "error": "Job not found"
}
```

**Example:**
```bash
curl http://localhost:5001/api/schedule/result/job-123
```

---

#### 3. GET /api/schedule/status/<job_id>

Get the status of a scheduling job (lightweight check).

**Path Parameters:**
- `job_id`: String (required) - Job identifier

**Response (200 OK):**
```json
{
  "job_id": "job-123",
  "status": "in_progress",
  "started_at": "2025-01-01T10:00:00",
  "completed_at": null,
  "failed_at": null
}
```

**Status Values:**
- `queued`: Job is queued for processing
- `in_progress`: Job is currently being processed
- `completed`: Job completed successfully
- `failed`: Job failed with error

**Example:**
```bash
curl http://localhost:5001/api/schedule/status/job-123
```

---

#### 4. GET /health

Health check endpoint for monitoring.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "AI Scheduling Service",
  "timestamp": "2025-01-01T10:00:00",
  "active_jobs": 2
}
```

**Example:**
```bash
curl http://localhost:5001/health
```

---

#### 5. GET /api/jobs

List all jobs (for debugging and monitoring).

**Response (200 OK):**
```json
{
  "jobs": {
    "job-123": {
      "status": "completed",
      "tenant_id": "tenant-1",
      "started_at": "2025-01-01T10:00:00",
      "completed_at": "2025-01-01T10:05:00"
    },
    "job-124": {
      "status": "in_progress",
      "tenant_id": "tenant-2",
      "started_at": "2025-01-01T10:10:00",
      "completed_at": null
    }
  }
}
```

**Example:**
```bash
curl http://localhost:5001/api/jobs
```

---

## Data Models

### Employee

Represents an employee with their attributes.

```python
@dataclass
class Employee:
    id: str                    # Unique employee identifier
    name: str                  # Employee name
    department: str            # Department name
    skills: List[str]          # List of skills
    availability: Dict[str, List[str]]  # day -> [time_slots]
    max_hours_per_week: int    # Maximum working hours per week
    preferences: Dict[str, Any]  # Additional preferences
```

**Example:**
```python
employee = Employee(
    id="EMP001",
    name="John Doe",
    department="Sales",
    skills=["communication", "negotiation"],
    availability={
        "monday": ["09:00-17:00"],
        "tuesday": ["09:00-17:00"]
    },
    max_hours_per_week=40,
    preferences={}
)
```

---

### Task

Represents a task that needs to be scheduled.

```python
@dataclass
class Task:
    id: str                    # Unique task identifier
    title: str                 # Task title
    department: str            # Department for task
    required_skills: List[str] # Skills required for task
    duration_hours: int        # Duration in hours
    priority: int              # Priority level (higher = more important)
    dependencies: List[str]    # List of task IDs this depends on
    preferred_time_slots: List[str]  # Preferred time slots
    deadline: Optional[datetime]  # Task deadline
```

**Example:**
```python
task = Task(
    id="task-001",
    title="Customer Meeting",
    department="Sales",
    required_skills=["communication"],
    duration_hours=2,
    priority=5,
    dependencies=[],
    preferred_time_slots=["09:00-17:00"],
    deadline=datetime(2025, 1, 7)
)
```

---

### ScheduleResult

Represents a scheduled assignment of a task to an employee.

```python
@dataclass
class ScheduleResult:
    task_id: str              # Task identifier
    employee_id: str           # Employee identifier
    start_time: datetime       # Scheduled start time
    end_time: datetime         # Scheduled end time
    department: str            # Department
    status: str                # Status (e.g., "scheduled")
```

**Example:**
```python
result = ScheduleResult(
    task_id="task-001",
    employee_id="EMP001",
    start_time=datetime(2025, 1, 1, 9, 0),
    end_time=datetime(2025, 1, 1, 17, 0),
    department="Sales",
    status="scheduled"
)
```

---

### JobStatus Enum

Job status enumeration.

```python
class JobStatus(Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
```

---

## Scheduling Algorithm

### DeterministicScheduler Class

The core scheduling algorithm that assigns tasks to employees.

#### Algorithm Overview

1. **Load Employees**: Load employee data from preschedule data
2. **Create Tasks**: Generate tasks from parameters
3. **Sort Tasks**: Sort by priority and deadline
4. **For Each Task**:
   - Find suitable employees (department, skills)
   - Select employee with least workload
   - Find available time slot
   - Assign task to employee
   - Update employee workload
5. **Return Results**: Return list of scheduled assignments

#### Key Methods

##### `load_preschedule_data(preschedule_data)`

Loads employee data from Google Sheets preschedule format.

**Input Format:**
```python
[
    ["employee_id", "name", "department", "skills", "availability", "max_hours"],
    ["EMP001", "John Doe", "Sales", "communication", "monday:09:00-17:00", "40"],
    ...
]
```

**Process:**
- Skips header row
- Parses each employee row
- Creates Employee objects
- Validates minimum required columns (4)

---

##### `create_tasks_from_parameters(parameters)`

Creates tasks based on scheduling parameters.

**Parameters:**
```python
{
    "task_count": 10,              # Number of tasks to create
    "departments": ["Sales", "IT"], # Department distribution
    "date_range": "2025-01-01 to 2025-01-07",  # Scheduling period
    "task_duration_hours": 8,       # Default task duration
    "task_priority": 1             # Default priority
}
```

**Process:**
- Parses date range
- Generates specified number of tasks
- Distributes tasks across departments
- Sets default duration and priority

---

##### `schedule_tasks()`

Main scheduling algorithm execution.

**Process:**
1. Sort tasks by priority (descending) and deadline (ascending)
2. Initialize employee workload tracker
3. For each task:
   - Find suitable employees
   - Select employee with minimum workload
   - Find available time slot
   - Create schedule result
   - Update workload
4. Return all schedule results

**Returns:**
```python
List[ScheduleResult]  # List of scheduled assignments
```

---

##### `_find_suitable_employees(task)`

Finds employees suitable for a given task.

**Criteria:**
- Department match (if task department is not "General")
- Skills match (if task requires specific skills)

**Returns:**
```python
List[Employee]  # List of suitable employees
```

---

##### `_find_available_time_slot(employee, task)`

Finds available time slot for employee and task.

**Current Implementation:**
- Simplified version
- Finds next Monday at 9 AM
- Calculates end time based on task duration

**Note:** This is a simplified implementation. In production, this should:
- Check employee availability
- Check existing schedule conflicts
- Respect maximum hours per week
- Consider preferred time slots

**Returns:**
```python
Optional[Dict[str, datetime]]  # {"start": datetime, "end": datetime}
```

---

## Installation & Setup

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Docker (optional, for containerized deployment)

### Local Development Setup

1. **Clone or navigate to ai_service directory:**
```bash
cd ai_service
```

2. **Create virtual environment (recommended):**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Run the service:**
```bash
python app.py
```

The service will start on `http://localhost:5001`

### Environment Variables

Currently, the service doesn't require environment variables for basic operation. However, you can configure:

- `PORT`: Service port (default: 5001)
- `DEBUG`: Enable debug mode (default: True in development)

### Verify Installation

```bash
curl http://localhost:5001/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "AI Scheduling Service",
  "timestamp": "...",
  "active_jobs": 0
}
```

---

## Usage Examples

### Example 1: Basic Scheduling Job

```python
import requests
import json
import time

# Service URL
BASE_URL = "http://localhost:5001"

# Prepare job data
job_data = {
    "job_id": "job-example-001",
    "tenant_id": "tenant-1",
    "preschedule_data": [
        ["ID", "Name", "Department", "Skills", "Availability", "Max Hours"],
        ["EMP001", "John Doe", "Sales", "communication", "monday:09:00-17:00", "40"],
        ["EMP002", "Jane Smith", "IT", "python", "tuesday:09:00-17:00", "40"],
        ["EMP003", "Bob Johnson", "Sales", "negotiation", "wednesday:09:00-17:00", "40"]
    ],
    "parameters": {
        "task_count": 5,
        "departments": ["Sales", "IT"],
        "date_range": "2025-01-01 to 2025-01-07",
        "task_duration_hours": 8,
        "task_priority": 1
    }
}

# Submit job
response = requests.post(
    f"{BASE_URL}/api/schedule/compute",
    json=job_data,
    headers={"Content-Type": "application/json"}
)

if response.status_code == 202:
    job_info = response.json()
    job_id = job_info["job_id"]
    print(f"Job {job_id} queued successfully")
    
    # Poll for completion
    while True:
        status_response = requests.get(f"{BASE_URL}/api/schedule/status/{job_id}")
        status = status_response.json()
        
        if status["status"] == "completed":
            # Get results
            result_response = requests.get(f"{BASE_URL}/api/schedule/result/{job_id}")
            result = result_response.json()
            
            print(f"Job completed!")
            print(f"Scheduled {len(result['result_data'])} tasks")
            print(f"Utilization rate: {result['summary']['utilization_rate']}")
            break
        elif status["status"] == "failed":
            print(f"Job failed: {status.get('error', 'Unknown error')}")
            break
        
        time.sleep(1)  # Poll every second
else:
    print(f"Error: {response.status_code} - {response.text}")
```

---

### Example 2: Check Job Status

```python
import requests

BASE_URL = "http://localhost:5001"
job_id = "job-123"

response = requests.get(f"{BASE_URL}/api/schedule/status/{job_id}")

if response.status_code == 200:
    status = response.json()
    print(f"Job Status: {status['status']}")
    print(f"Started: {status.get('started_at')}")
    print(f"Completed: {status.get('completed_at', 'Not completed')}")
elif response.status_code == 404:
    print("Job not found")
```

---

### Example 3: List All Jobs

```python
import requests

BASE_URL = "http://localhost:5001"

response = requests.get(f"{BASE_URL}/api/jobs")

if response.status_code == 200:
    jobs = response.json()["jobs"]
    print(f"Total jobs: {len(jobs)}")
    
    for job_id, job_info in jobs.items():
        print(f"\nJob {job_id}:")
        print(f"  Status: {job_info['status']}")
        print(f"  Tenant: {job_info['tenant_id']}")
        print(f"  Started: {job_info.get('started_at')}")
```

---

### Example 4: Integration with Main Backend

The AI service is typically called from the main backend application:

```python
# In main backend (Flask app)
import requests

def trigger_scheduling(schedule_def_id, preschedule_data):
    """Trigger scheduling job in AI service"""
    
    job_id = f"job-{schedule_def_id}-{int(time.time())}"
    
    payload = {
        "job_id": job_id,
        "tenant_id": current_user.tenantID,
        "preschedule_data": preschedule_data,
        "parameters": {
            "task_count": 10,
            "departments": ["Sales", "IT"],
            "date_range": "2025-01-01 to 2025-01-07"
        }
    }
    
    response = requests.post(
        "http://ai-service:5001/api/schedule/compute",
        json=payload
    )
    
    if response.status_code == 202:
        return {"job_id": job_id, "status": "queued"}
    else:
        raise Exception(f"Scheduling failed: {response.text}")
```

---

## Deployment

### Docker Deployment

#### Build Docker Image

```bash
cd ai_service
docker build -t ai-scheduling-service:latest .
```

#### Run Container

```bash
docker run -d \
  --name ai-scheduling-service \
  -p 5001:5001 \
  ai-scheduling-service:latest
```

#### Docker Compose (Example)

```yaml
version: '3.8'

services:
  ai-scheduling-service:
    build: ./ai_service
    ports:
      - "5001:5001"
    environment:
      - PORT=5001
      - DEBUG=false
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

### Production Considerations

#### 1. Job Storage

**Current Implementation:** In-memory dictionary  
**Production Recommendation:** Use Redis or database

```python
# Example with Redis
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def store_job(job_id, job_data):
    redis_client.setex(
        f"job:{job_id}",
        3600,  # TTL: 1 hour
        json.dumps(job_data)
    )
```

#### 2. Task Queue

**Current Implementation:** Background threads  
**Production Recommendation:** Use Celery or RQ

```python
# Example with Celery
from celery import Celery

celery_app = Celery('ai_scheduler')

@celery_app.task
def process_scheduling_job(job_id, tenant_id, preschedule_data, parameters):
    # Scheduling logic here
    pass
```

#### 3. Error Handling

- Implement retry logic
- Add comprehensive error logging
- Set up monitoring and alerting

#### 4. Scaling

- Use load balancer for multiple instances
- Implement job queue (Redis Queue, RabbitMQ)
- Use container orchestration (Kubernetes, Docker Swarm)

---

## Error Handling

### Common Errors

#### 1. Job Not Found (404)

**Cause:** Job ID doesn't exist  
**Solution:** Verify job_id before querying

```python
if job_id not in jobs:
    return jsonify({'error': 'Job not found'}), 404
```

#### 2. Missing Required Fields (400)

**Cause:** Missing `job_id` or `tenant_id`  
**Solution:** Validate request data

```python
if not job_id or not tenant_id:
    return jsonify({'error': 'job_id and tenant_id are required'}), 400
```

#### 3. Processing Error (500)

**Cause:** Exception during scheduling algorithm  
**Solution:** Check logs, validate input data format

```python
try:
    results = scheduler.schedule_tasks()
except Exception as e:
    logger.error(f"Scheduling error: {str(e)}")
    # Update job status to failed
```

---

## Limitations & Future Improvements

### Current Limitations

1. **In-Memory Storage**: Jobs stored in memory (lost on restart)
2. **Simple Time Slot Finding**: Doesn't check actual availability conflicts
3. **No Task Dependencies**: Dependency structure exists but not enforced
4. **No Skill Matching**: Skills list exists but matching is basic
5. **No Optimization**: No optimization for workload balancing or preferences
6. **Single Thread**: Background threads, but no proper task queue

### Future Improvements

1. **Persistent Storage**: Use Redis or database for job storage
2. **Advanced Scheduling**: 
   - Constraint satisfaction problem (CSP) solver
   - Genetic algorithms for optimization
   - Machine learning for preference learning
3. **Real Availability Checking**: Check against existing schedules
4. **Task Dependencies**: Implement dependency resolution
5. **Skill Matching**: Advanced skill matching with proficiency levels
6. **Workload Optimization**: Optimize for balanced workload
7. **Priority Queuing**: Implement priority queue for jobs
8. **Caching**: Cache employee data and availability
9. **API Versioning**: Add versioning to API endpoints
10. **Authentication**: Add authentication/authorization
11. **Rate Limiting**: Implement rate limiting
12. **Metrics**: Add Prometheus metrics endpoint

---

## Testing

### Manual Testing

```bash
# Health check
curl http://localhost:5001/health

# Submit job
curl -X POST http://localhost:5001/api/schedule/compute \
  -H "Content-Type: application/json" \
  -d @test_job.json

# Check status
curl http://localhost:5001/api/schedule/status/job-123

# Get results
curl http://localhost:5001/api/schedule/result/job-123
```

### Unit Testing (Future)

```python
import pytest
from app import DeterministicScheduler, Employee, Task

def test_scheduler_initialization():
    scheduler = DeterministicScheduler()
    assert scheduler.employees == []
    assert scheduler.tasks == []

def test_load_employees():
    scheduler = DeterministicScheduler()
    preschedule_data = [
        ["ID", "Name", "Department", "Skills"],
        ["EMP001", "John", "Sales", "communication"]
    ]
    scheduler.load_preschedule_data(preschedule_data)
    assert len(scheduler.employees) == 1
```

---

## Monitoring & Logging

### Logging

The service uses Python's `logging` module:

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

**Log Levels:**
- `INFO`: General information (job queued, completed)
- `WARNING`: Non-critical issues (no suitable employees)
- `ERROR`: Errors during processing

### Monitoring

**Health Endpoint:** `/health`

**Metrics to Monitor:**
- Active jobs count
- Job completion rate
- Average processing time
- Error rate

---

## Security Considerations

### Current State

- No authentication
- No authorization
- No input validation (beyond basic checks)
- No rate limiting

### Recommendations

1. **Add Authentication**: JWT tokens or API keys
2. **Input Validation**: Validate all input data
3. **Rate Limiting**: Prevent abuse
4. **CORS**: Configure CORS properly
5. **HTTPS**: Use HTTPS in production
6. **Input Sanitization**: Sanitize all user inputs

---

## Support & Troubleshooting

### Common Issues

#### Service won't start

**Check:**
- Port 5001 is available
- Python 3.9+ is installed
- Dependencies are installed

#### Jobs not processing

**Check:**
- Background threads are running
- No exceptions in logs
- Input data format is correct

#### Jobs failing

**Check:**
- Preschedule data format
- Parameters are valid
- Logs for error messages

---

## License

This service is part of the Project_Up scheduling system.

---

## Contact & Contribution

For issues, questions, or contributions, please refer to the main project documentation.

