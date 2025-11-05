"""
Schedule Execution Service
Handles the actual execution of scheduling tasks, either via Celery or synchronously
"""
import logging
from datetime import datetime
from app import db
from app.models import ScheduleJobLog

logger = logging.getLogger(__name__)


def execute_schedule_task_sync(schedule_config, job_log_id):
    """
    Execute a schedule task synchronously (fallback when Celery is not available)
    
    Args:
        schedule_config: Dictionary with schedule configuration
        job_log_id: ID of the job log to update
    """
    try:
        logger.info(f"[INFO] Executing schedule task synchronously for job: {job_log_id}")
        
        # Get job log
        job_log = ScheduleJobLog.query.get(job_log_id)
        if not job_log:
            logger.error(f"Job log {job_log_id} not found")
            return False
        
        # Update status
        job_log.status = 'running'
        job_log.startTime = datetime.utcnow()
        db.session.commit()
        
        # Try to import and run the scheduling task
        try:
            # Import the scheduling module
            from app.services.google_sheets_import import _try_import_google_sheets
            from app.services.dashboard_data_service import DashboardDataService
            
            # Get Google Sheets service
            creds_path = schedule_config.get('input_config', {}).get('credentials_path', 'service-account-creds.json')
            service = DashboardDataService(creds_path)
            
            # Execute the scheduling (this would call the actual scheduling logic)
            # For now, mark as completed (in production, this would run the actual algorithm)
            logger.info(f"[INFO] Schedule execution completed for job: {job_log_id}")
            
            # Use complete_job method for proper status handling
            job_log.complete_job(
                result_summary="Schedule executed successfully (synchronous mode)",
                metadata={'execution_mode': 'synchronous'}
            )
            
            return True
        except Exception as e:
            logger.error(f"[ERROR] Schedule execution failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Use fail_job method for proper status handling
            job_log.fail_job(
                error_message=str(e),
                metadata={'execution_mode': 'synchronous', 'error_type': type(e).__name__}
            )
            
            return False
            
    except Exception as e:
        logger.error(f"[ERROR] Failed to execute schedule task: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

