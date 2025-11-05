# AI Scheduling Service Microservice
from flask import Flask, request, jsonify
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import uuid
from dataclasses import dataclass
from enum import Enum
import threading
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class JobStatus(Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Employee:
    id: str
    name: str
    department: str
    skills: List[str]
    availability: Dict[str, List[str]]  # day -> [time_slots]
    max_hours_per_week: int
    preferences: Dict[str, Any]

@dataclass
class Task:
    id: str
    title: str
    department: str
    required_skills: List[str]
    duration_hours: int
    priority: int
    dependencies: List[str]
    preferred_time_slots: List[str]
    deadline: Optional[datetime]

@dataclass
class ScheduleResult:
    task_id: str
    employee_id: str
    start_time: datetime
    end_time: datetime
    department: str
    status: str

class DeterministicScheduler:
    """Deterministic scheduling algorithm that respects constraints"""
    
    def __init__(self):
        self.employees = []
        self.tasks = []
        self.schedule_results = []
    
    def load_preschedule_data(self, preschedule_data: List[List[str]]) -> None:
        """Load preschedule data from Google Sheets"""
        try:
            if not preschedule_data or len(preschedule_data) < 2:
                logger.warning("No preschedule data provided")
                return
            
            # Skip header row
            for row in preschedule_data[1:]:
                if len(row) >= 4:  # Ensure minimum required columns
                    employee = Employee(
                        id=row[0] if len(row) > 0 else str(uuid.uuid4()),
                        name=row[1] if len(row) > 1 else f"Employee {row[0]}",
                        department=row[2] if len(row) > 2 else "General",
                        skills=row[3].split(',') if len(row) > 3 and row[3] else [],
                        availability=self._parse_availability(row[4] if len(row) > 4 else ""),
                        max_hours_per_week=int(row[5]) if len(row) > 5 and row[5].isdigit() else 40,
                        preferences={}
                    )
                    self.employees.append(employee)
            
            logger.info(f"Loaded {len(self.employees)} employees from preschedule data")
            
        except Exception as e:
            logger.error(f"Error loading preschedule data: {str(e)}")
            raise
    
    def _parse_availability(self, availability_str: str) -> Dict[str, List[str]]:
        """Parse availability string into structured format"""
        availability = {}
        if not availability_str:
            # Default availability: Monday to Friday, 9 AM to 5 PM
            for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
                availability[day] = ['09:00-17:00']
        else:
            # Parse availability string (simplified)
            # Format: "monday:09:00-17:00,tuesday:09:00-17:00,..."
            try:
                for day_slot in availability_str.split(','):
                    if ':' in day_slot:
                        day, time_slot = day_slot.split(':', 1)
                        availability[day.strip().lower()] = [time_slot.strip()]
            except:
                # Fallback to default
                for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
                    availability[day] = ['09:00-17:00']
        
        return availability
    
    def create_tasks_from_parameters(self, parameters: Dict[str, Any]) -> None:
        """Create tasks based on scheduling parameters"""
        try:
            # Extract task information from parameters
            task_count = parameters.get('task_count', 10)
            departments = parameters.get('departments', ['General'])
            date_range = parameters.get('date_range', '2025-01-01 to 2025-01-07')
            
            # Parse date range
            start_date, end_date = self._parse_date_range(date_range)
            
            # Generate tasks
            for i in range(task_count):
                task = Task(
                    id=str(uuid.uuid4()),
                    title=f"Task {i+1}",
                    department=departments[i % len(departments)],
                    required_skills=[],
                    duration_hours=parameters.get('task_duration_hours', 8),
                    priority=parameters.get('task_priority', 1),
                    dependencies=[],
                    preferred_time_slots=['09:00-17:00'],
                    deadline=end_date
                )
                self.tasks.append(task)
            
            logger.info(f"Created {len(self.tasks)} tasks")
            
        except Exception as e:
            logger.error(f"Error creating tasks: {str(e)}")
            raise
    
    def _parse_date_range(self, date_range: str) -> tuple:
        """Parse date range string"""
        try:
            if ' to ' in date_range:
                start_str, end_str = date_range.split(' to ')
                start_date = datetime.strptime(start_str.strip(), '%Y-%m-%d')
                end_date = datetime.strptime(end_str.strip(), '%Y-%m-%d')
            else:
                start_date = datetime.now()
                end_date = start_date + timedelta(days=7)
            
            return start_date, end_date
        except:
            start_date = datetime.now()
            end_date = start_date + timedelta(days=7)
            return start_date, end_date
    
    def schedule_tasks(self) -> List[ScheduleResult]:
        """Main scheduling algorithm"""
        try:
            logger.info("Starting scheduling algorithm")
            
            # Sort tasks by priority and deadline
            sorted_tasks = sorted(self.tasks, key=lambda t: (t.priority, t.deadline or datetime.max))
            
            # Track employee workload
            employee_workload = {emp.id: 0 for emp in self.employees}
            
            for task in sorted_tasks:
                # Find suitable employees for this task
                suitable_employees = self._find_suitable_employees(task)
                
                if not suitable_employees:
                    logger.warning(f"No suitable employees found for task {task.id}")
                    continue
                
                # Select best employee (least loaded)
                best_employee = min(suitable_employees, key=lambda emp: employee_workload[emp.id])
                
                # Find available time slot
                time_slot = self._find_available_time_slot(best_employee, task)
                
                if time_slot:
                    # Create schedule result
                    result = ScheduleResult(
                        task_id=task.id,
                        employee_id=best_employee.id,
                        start_time=time_slot['start'],
                        end_time=time_slot['end'],
                        department=task.department,
                        status='scheduled'
                    )
                    
                    self.schedule_results.append(result)
                    employee_workload[best_employee.id] += task.duration_hours
                    
                    logger.info(f"Scheduled task {task.id} to employee {best_employee.id}")
                else:
                    logger.warning(f"No available time slot found for task {task.id}")
            
            logger.info(f"Scheduling completed. {len(self.schedule_results)} tasks scheduled")
            return self.schedule_results
            
        except Exception as e:
            logger.error(f"Error in scheduling algorithm: {str(e)}")
            raise
    
    def _find_suitable_employees(self, task: Task) -> List[Employee]:
        """Find employees suitable for a task"""
        suitable = []
        
        for employee in self.employees:
            # Check department match
            if task.department != 'General' and employee.department != task.department:
                continue
            
            # Check skills match (if required)
            if task.required_skills:
                if not any(skill in employee.skills for skill in task.required_skills):
                    continue
            
            suitable.append(employee)
        
        return suitable
    
    def _find_available_time_slot(self, employee: Employee, task: Task) -> Optional[Dict[str, datetime]]:
        """Find available time slot for employee and task"""
        # Simplified time slot finding
        # In a real implementation, this would check against existing schedule
        
        # Start from next Monday at 9 AM
        start_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        while start_time.weekday() != 0:  # Monday
            start_time += timedelta(days=1)
        
        end_time = start_time + timedelta(hours=task.duration_hours)
        
        return {
            'start': start_time,
            'end': end_time
        }

# In-memory job storage (in production, use Redis or database)
jobs = {}

def process_job_async(job_id: str, tenant_id: str, preschedule_data: List[List[str]], parameters: Dict[str, Any]):
    """Process scheduling job asynchronously"""
    try:
        logger.info(f"Processing job {job_id}")
        
        # Update job status
        jobs[job_id] = {
            'status': JobStatus.IN_PROGRESS.value,
            'started_at': datetime.utcnow().isoformat(),
            'tenant_id': tenant_id
        }
        
        # Create scheduler instance
        scheduler = DeterministicScheduler()
        
        # Load preschedule data
        scheduler.load_preschedule_data(preschedule_data)
        
        # Create tasks from parameters
        scheduler.create_tasks_from_parameters(parameters)
        
        # Run scheduling algorithm
        results = scheduler.schedule_tasks()
        
        # Prepare result data
        result_data = []
        for result in results:
            result_data.append({
                'task_id': result.task_id,
                'employee_id': result.employee_id,
                'employee_name': next((emp.name for emp in scheduler.employees if emp.id == result.employee_id), 'Unknown'),
                'start_time': result.start_time.isoformat(),
                'end_time': result.end_time.isoformat(),
                'department': result.department,
                'status': result.status,
                'duration_hours': (result.end_time - result.start_time).total_seconds() / 3600
            })
        
        # Update job status to completed
        jobs[job_id] = {
            'status': JobStatus.COMPLETED.value,
            'started_at': jobs[job_id]['started_at'],
            'completed_at': datetime.utcnow().isoformat(),
            'tenant_id': tenant_id,
            'result_data': result_data,
            'summary': {
                'total_tasks': len(scheduler.tasks),
                'scheduled_tasks': len(results),
                'total_employees': len(scheduler.employees),
                'utilization_rate': len(results) / len(scheduler.tasks) if scheduler.tasks else 0
            }
        }
        
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}")
        jobs[job_id] = {
            'status': JobStatus.FAILED.value,
            'started_at': jobs.get(job_id, {}).get('started_at', datetime.utcnow().isoformat()),
            'failed_at': datetime.utcnow().isoformat(),
            'tenant_id': tenant_id,
            'error': str(e)
        }

@app.route('/api/schedule/compute', methods=['POST'])
def compute_schedule():
    """Start scheduling computation"""
    try:
        data = request.get_json()
        
        job_id = data.get('job_id')
        tenant_id = data.get('tenant_id')
        preschedule_data = data.get('preschedule_data', [])
        parameters = data.get('parameters', {})
        
        if not job_id or not tenant_id:
            return jsonify({'error': 'job_id and tenant_id are required'}), 400
        
        # Initialize job
        jobs[job_id] = {
            'status': JobStatus.QUEUED.value,
            'queued_at': datetime.utcnow().isoformat(),
            'tenant_id': tenant_id
        }
        
        # Start processing in background thread
        thread = threading.Thread(
            target=process_job_async,
            args=(job_id, tenant_id, preschedule_data, parameters)
        )
        thread.daemon = True
        thread.start()
        
        logger.info(f"Scheduling job {job_id} queued for tenant {tenant_id}")
        
        return jsonify({
            'job_id': job_id,
            'status': JobStatus.QUEUED.value,
            'message': 'Scheduling job queued successfully'
        }), 202
        
    except Exception as e:
        logger.error(f"Error starting schedule computation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedule/result/<job_id>', methods=['GET'])
def get_schedule_result(job_id: str):
    """Get scheduling result"""
    try:
        if job_id not in jobs:
            return jsonify({'error': 'Job not found'}), 404
        
        job = jobs[job_id]
        
        return jsonify({
            'job_id': job_id,
            'status': job['status'],
            'started_at': job.get('started_at'),
            'completed_at': job.get('completed_at'),
            'failed_at': job.get('failed_at'),
            'result_data': job.get('result_data'),
            'summary': job.get('summary'),
            'error': job.get('error')
        })
        
    except Exception as e:
        logger.error(f"Error getting schedule result: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedule/status/<job_id>', methods=['GET'])
def get_job_status(job_id: str):
    """Get job status"""
    try:
        if job_id not in jobs:
            return jsonify({'error': 'Job not found'}), 404
        
        job = jobs[job_id]
        
        return jsonify({
            'job_id': job_id,
            'status': job['status'],
            'started_at': job.get('started_at'),
            'completed_at': job.get('completed_at'),
            'failed_at': job.get('failed_at')
        })
        
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'AI Scheduling Service',
        'timestamp': datetime.utcnow().isoformat(),
        'active_jobs': len([j for j in jobs.values() if j['status'] == JobStatus.IN_PROGRESS.value])
    })

@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """List all jobs (for debugging)"""
    return jsonify({
        'jobs': {
            job_id: {
                'status': job['status'],
                'tenant_id': job['tenant_id'],
                'started_at': job.get('started_at'),
                'completed_at': job.get('completed_at')
            }
            for job_id, job in jobs.items()
        }
    })

if __name__ == '__main__':
    logger.info("Starting AI Scheduling Service")
    app.run(debug=True, host='0.0.0.0', port=5001)












