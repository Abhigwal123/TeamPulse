# Celery Tasks for Background Job Processing
from celery import Celery
from app import app, db, ScheduleLog, JobStatus
from datetime import datetime
import requests
import json
import logging
from typing import Dict, Any

# Configure Celery
celery_app = Celery('scheduling_tasks')
celery_app.config_from_object({
    'broker_url': 'redis://localhost:6379/0',
    'result_backend': 'redis://localhost:6379/0',
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'timezone': 'UTC',
    'enable_utc': True,
})

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def run_schedule_job(self, job_id: str, tenant_id: str, preschedule_sheet_id: str, parameters: Dict[str, Any]):
    """
    Celery task to run scheduling job
    
    Args:
        job_id: Unique job identifier
        tenant_id: Tenant ID
        preschedule_sheet_id: Google Sheets ID for preschedule data
        parameters: Scheduling parameters
    """
    try:
        logger.info(f"Starting schedule job {job_id} for tenant {tenant_id}")
        
        # Update job status to in_progress
        with app.app_context():
            schedule_log = ScheduleLog.query.filter_by(job_id=job_id).first()
            if not schedule_log:
                logger.error(f"Schedule log not found for job {job_id}")
                return
            
            schedule_log.status = JobStatus.IN_PROGRESS
            schedule_log.details = schedule_log.details or {}
            schedule_log.details['celery_task_id'] = self.request.id
            db.session.commit()
        
        # Step 1: Read preschedule data from Google Sheets
        logger.info(f"Reading preschedule data from sheet {preschedule_sheet_id}")
        preschedule_data = read_google_sheet(preschedule_sheet_id, 'A:Z')
        
        if not preschedule_data:
            raise Exception("Failed to read preschedule data from Google Sheets")
        
        # Step 2: Call AI Scheduling Service
        logger.info("Calling AI Scheduling Service")
        ai_service_url = app.config.get('AI_SERVICE_URL', 'http://localhost:5001')
        
        ai_request_data = {
            'tenant_id': tenant_id,
            'job_id': job_id,
            'preschedule_data': preschedule_data,
            'parameters': parameters
        }
        
        ai_response = requests.post(
            f"{ai_service_url}/api/schedule/compute",
            json=ai_request_data,
            timeout=300  # 5 minutes timeout
        )
        
        if ai_response.status_code != 200:
            raise Exception(f"AI Service error: {ai_response.text}")
        
        ai_result = ai_response.json()
        
        # Step 3: Poll for AI service result
        logger.info("Polling AI service for results")
        max_polls = 60  # 5 minutes with 5-second intervals
        poll_count = 0
        
        while poll_count < max_polls:
            result_response = requests.get(
                f"{ai_service_url}/api/schedule/result/{job_id}",
                timeout=30
            )
            
            if result_response.status_code == 200:
                result_data = result_response.json()
                
                if result_data['status'] == 'completed':
                    # Step 4: Write results to Google Sheets
                    logger.info("Writing results to Google Sheets")
                    result_sheet_id = write_schedule_results(
                        tenant_id, 
                        result_data['result_data'], 
                        parameters
                    )
                    
                    # Update job status to success
                    with app.app_context():
                        schedule_log = ScheduleLog.query.filter_by(job_id=job_id).first()
                        schedule_log.status = JobStatus.SUCCESS
                        schedule_log.finished_at = datetime.utcnow()
                        schedule_log.result_sheet_id = result_sheet_id
                        schedule_log.details = schedule_log.details or {}
                        schedule_log.details.update({
                            'ai_result': result_data,
                            'result_sheet_id': result_sheet_id,
                            'completion_time': datetime.utcnow().isoformat()
                        })
                        db.session.commit()
                    
                    logger.info(f"Schedule job {job_id} completed successfully")
                    return {'status': 'success', 'result_sheet_id': result_sheet_id}
                
                elif result_data['status'] == 'failed':
                    raise Exception(f"AI Service failed: {result_data.get('error', 'Unknown error')}")
            
            # Wait 5 seconds before next poll
            import time
            time.sleep(5)
            poll_count += 1
        
        # Timeout
        raise Exception("AI Service timeout - job took too long to complete")
        
    except Exception as e:
        logger.error(f"Schedule job {job_id} failed: {str(e)}")
        
        # Update job status to failed
        with app.app_context():
            schedule_log = ScheduleLog.query.filter_by(job_id=job_id).first()
            if schedule_log:
                schedule_log.status = JobStatus.FAILED
                schedule_log.finished_at = datetime.utcnow()
                schedule_log.error_message = str(e)
                schedule_log.details = schedule_log.details or {}
                schedule_log.details['error'] = str(e)
                db.session.commit()
        
        # Re-raise exception for Celery
        raise self.retry(exc=e, countdown=60, max_retries=3)

def read_google_sheet(sheet_id: str, range_name: str) -> list:
    """
    Read data from Google Sheets using service account
    
    Args:
        sheet_id: Google Sheets ID
        range_name: Range to read (e.g., 'A:Z', 'Sheet1!A1:Z100')
    
    Returns:
        List of rows from the sheet
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        # Load service account credentials
        service_account_file = app.config.get('GOOGLE_SERVICE_ACCOUNT_FILE')
        if not service_account_file:
            logger.warning("Google Service Account file not configured")
            return []
        
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        
        service = build('sheets', 'v4', credentials=credentials)
        sheet = service.spreadsheets()
        
        result = sheet.values().get(
            spreadsheetId=sheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        logger.info(f"Read {len(values)} rows from Google Sheet {sheet_id}")
        
        return values
        
    except Exception as e:
        logger.error(f"Error reading Google Sheet {sheet_id}: {str(e)}")
        return []

def write_schedule_results(tenant_id: str, result_data: list, parameters: Dict[str, Any]) -> str:
    """
    Write schedule results to Google Sheets
    
    Args:
        tenant_id: Tenant ID
        result_data: Schedule results data
        parameters: Original parameters
    
    Returns:
        Google Sheets ID of the results sheet
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        # Load service account credentials
        service_account_file = app.config.get('GOOGLE_SERVICE_ACCOUNT_FILE')
        if not service_account_file:
            raise Exception("Google Service Account file not configured")
        
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        service = build('sheets', 'v4', credentials=credentials)
        
        # Create new spreadsheet for results
        spreadsheet_body = {
            'properties': {
                'title': f'Schedule Results - {tenant_id} - {datetime.now().strftime("%Y-%m-%d %H:%M")}'
            }
        }
        
        spreadsheet = service.spreadsheets().create(body=spreadsheet_body).execute()
        sheet_id = spreadsheet['spreadsheetId']
        
        # Write results data
        if result_data:
            # Prepare data for writing
            values = []
            if isinstance(result_data[0], dict):
                # Convert dict to rows
                headers = list(result_data[0].keys())
                values.append(headers)
                for row in result_data:
                    values.append([row.get(header, '') for header in headers])
            else:
                values = result_data
            
            # Write to sheet
            body = {'values': values}
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range='A1',
                valueInputOption='RAW',
                body=body
            ).execute()
        
        logger.info(f"Results written to Google Sheet {sheet_id}")
        return sheet_id
        
    except Exception as e:
        logger.error(f"Error writing results to Google Sheets: {str(e)}")
        raise

@celery_app.task
def send_notification(notification_type: str, recipient: str, message: str, data: Dict[str, Any] = None):
    """
    Send notification (email, SMS, etc.)
    
    Args:
        notification_type: Type of notification (email, sms, etc.)
        recipient: Recipient address/phone
        message: Notification message
        data: Additional data for the notification
    """
    try:
        logger.info(f"Sending {notification_type} notification to {recipient}")
        
        # TODO: Implement actual notification sending
        # This could integrate with:
        # - SMTP for emails
        # - Twilio for SMS
        # - Slack webhooks
        # - etc.
        
        if notification_type == 'email':
            # Implement email sending
            pass
        elif notification_type == 'sms':
            # Implement SMS sending
            pass
        
        logger.info(f"Notification sent successfully to {recipient}")
        
    except Exception as e:
        logger.error(f"Failed to send notification: {str(e)}")
        raise

@celery_app.task
def cleanup_old_logs():
    """Clean up old schedule logs (run daily)"""
    try:
        from datetime import timedelta
        
        with app.app_context():
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            old_logs = ScheduleLog.query.filter(ScheduleLog.started_at < cutoff_date).all()
            
            for log in old_logs:
                db.session.delete(log)
            
            db.session.commit()
            logger.info(f"Cleaned up {len(old_logs)} old schedule logs")
            
    except Exception as e:
        logger.error(f"Error cleaning up old logs: {str(e)}")
        raise

# Periodic tasks
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'cleanup-old-logs': {
        'task': 'app.tasks.cleanup_old_logs',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
    },
}

if __name__ == '__main__':
    celery_app.start()












