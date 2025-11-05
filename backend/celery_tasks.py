"""
Celery tasks for asynchronous scheduling operations
"""
import os
import sys
import json
import traceback
import logging
from datetime import datetime
from celery import current_task
from celery_config import celery

logger = logging.getLogger(__name__)

# Add the project root to Python path to import app modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from run_refactored import run_schedule_task
except ImportError as e:
    print(f"Warning: Could not import run_schedule_task: {e}")
    run_schedule_task = None

@celery.task(bind=True, name='celery_tasks.execute_scheduling_task')
def execute_scheduling_task(self, schedule_config, job_log_id=None):
    """
    Execute scheduling task asynchronously using the existing CP-SAT engine
    
    Args:
        schedule_config: Dictionary containing scheduling configuration
        job_log_id: Optional job log ID to update after completion
        
    Returns:
        Dictionary with task results and status
    """
    task_id = self.request.id
    job_log_id = job_log_id or schedule_config.get('job_log_id')
    
    try:
        # Update task state to STARTED
        self.update_state(
            state='STARTED',
            meta={
                'status': 'Processing scheduling request...',
                'progress': 0,
                'task_id': task_id,
                'started_at': datetime.utcnow().isoformat()
            }
        )
        
        if not run_schedule_task:
            raise Exception("Scheduling engine not available")
        
        # Extract configuration from request
        input_source = schedule_config.get('input_source', 'excel')
        input_config = schedule_config.get('input_config', {})
        output_destination = schedule_config.get('output_destination', 'excel')
        output_config = schedule_config.get('output_config', {})
        time_limit = schedule_config.get('time_limit', 90.0)
        debug_shift = schedule_config.get('debug_shift')
        log_level = schedule_config.get('log_level', 'INFO')
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'Loading input data...',
                'progress': 20,
                'task_id': task_id
            }
        )
        
        # Execute the scheduling task
        result = run_schedule_task(
            input_source=input_source,
            input_config=input_config,
            output_destination=output_destination,
            output_config=output_config,
            time_limit=time_limit,
            debug_shift=debug_shift,
            log_level=log_level
        )
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'Scheduling completed successfully',
                'progress': 90,
                'task_id': task_id
            }
        )
        
        # Update job log if job_log_id is provided
        if job_log_id:
            try:
                # Import here to avoid circular dependencies
                from app import create_app, db
                from app.models import ScheduleJobLog
                
                app = create_app()
                with app.app_context():
                    job_log = ScheduleJobLog.query.get(job_log_id)
                    if job_log:
                        result_summary = f"Scheduling completed. Task: {task_id}"
                        job_log.complete_job(
                            result_summary=result_summary,
                            metadata={
                                'celery_task_id': task_id,
                                'result': result
                            }
                        )
                        logger.info(f"Job log {job_log_id} updated to success")
            except Exception as e:
                logger.error(f"Failed to update job log {job_log_id}: {str(e)}")
        
        # Prepare final result
        final_result = {
            'status': 'SUCCESS',
            'task_id': task_id,
            'completed_at': datetime.utcnow().isoformat(),
            'result': result,
            'message': 'Scheduling task completed successfully',
            'job_log_id': job_log_id
        }
        
        # Update final state
        self.update_state(
            state='SUCCESS',
            meta=final_result
        )
        
        return final_result
        
    except Exception as e:
        error_msg = str(e)
        error_traceback = traceback.format_exc()
        
        # Log the error
        print(f"Task {task_id} failed: {error_msg}")
        print(f"Traceback: {error_traceback}")
        
        # Update job log if job_log_id is provided
        if job_log_id:
            try:
                from app import create_app, db
                from app.models import ScheduleJobLog
                
                app = create_app()
                with app.app_context():
                    job_log = ScheduleJobLog.query.get(job_log_id)
                    if job_log:
                        job_log.fail_job(
                            error_message=error_msg,
                            metadata={
                                'celery_task_id': task_id,
                                'traceback': error_traceback
                            }
                        )
                        logger.info(f"Job log {job_log_id} updated to failed")
            except Exception as e:
                logger.error(f"Failed to update job log {job_log_id}: {str(e)}")
        
        # Update task state to FAILURE
        error_result = {
            'status': 'FAILURE',
            'task_id': task_id,
            'failed_at': datetime.utcnow().isoformat(),
            'error': error_msg,
            'traceback': error_traceback,
            'message': 'Scheduling task failed',
            'job_log_id': job_log_id
        }
        
        self.update_state(
            state='FAILURE',
            meta=error_result
        )
        
        return error_result

@celery.task(name='celery_tasks.test_task')
def test_task():
    """
    Simple test task to verify Celery is working
    """
    return {
        'status': 'SUCCESS',
        'message': 'Celery is working correctly',
        'timestamp': datetime.utcnow().isoformat()
    }




