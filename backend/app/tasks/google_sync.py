"""
Google Sheets Sync Tasks
Celery tasks for periodic synchronization of Google Sheets data to database
"""
from app.tasks.celery_app import celery
from app import db
from app.models import ScheduleDefinition, SyncLog
from app.services.google_sheets_sync_service import GoogleSheetsSyncService
from flask import current_app
import logging

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.google_sync.sync_google_sheets_daily", bind=True)
def sync_google_sheets_daily(self):
    """
    Daily sync task - syncs all active schedule definitions
    Runs periodically via Celery Beat
    """
    with current_app.app_context():
        try:
            logger.info("[SYNC] Starting daily Google Sheets sync task")
            
            # Get all active schedule definitions
            schedules = ScheduleDefinition.query.filter_by(is_active=True).all()
            
            if not schedules:
                logger.info("[SYNC] No active schedules found, skipping sync")
                return {"success": True, "message": "No active schedules to sync"}
            
            # Get credentials path
            creds_path = current_app.config.get('GOOGLE_APPLICATION_CREDENTIALS', 'service-account-creds.json')
            sync_service = GoogleSheetsSyncService(creds_path)
            
            results = []
            for schedule_def in schedules:
                try:
                    # Check if sync is needed (not forced for auto syncs)
                    if not SyncLog.should_sync(schedule_def_id=schedule_def.scheduleDefID, min_minutes=10):
                        logger.info(f"[SYNC] Skipped schedule {schedule_def.scheduleDefID} (data fresh, last_synced_at={SyncLog.get_last_sync(schedule_def_id=schedule_def.scheduleDefID).completed_at if SyncLog.get_last_sync(schedule_def_id=schedule_def.scheduleDefID) else 'Never'})")
                        continue
                    
                    result = sync_service.sync_schedule_data(
                        schedule_def_id=schedule_def.scheduleDefID,
                        sync_type='scheduled',
                        triggered_by=None,
                        force=False
                    )
                    
                    results.append({
                        'schedule_def_id': schedule_def.scheduleDefID,
                        'schedule_name': schedule_def.scheduleName,
                        **result
                    })
                    
                except Exception as e:
                    logger.error(f"[SYNC] Error syncing schedule {schedule_def.scheduleDefID}: {str(e)}")
                    results.append({
                        'schedule_def_id': schedule_def.scheduleDefID,
                        'schedule_name': schedule_def.scheduleName,
                        'success': False,
                        'error': str(e)
                    })
            
            success_count = len([r for r in results if r.get('success', False)])
            logger.info(f"[SYNC] Daily sync completed: {success_count}/{len(results)} schedules synced")
            
            return {
                'success': True,
                'schedules_synced': success_count,
                'total_schedules': len(results),
                'results': results
            }
            
        except Exception as e:
            logger.error(f"[SYNC] Daily sync task failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise


@celery.task(name="app.tasks.google_sync.sync_schedule_definition", bind=True)
def sync_schedule_definition(self, schedule_def_id: str, force: bool = False):
    """
    Sync a specific schedule definition
    
    Args:
        schedule_def_id: Schedule definition ID to sync
        force: Force sync even if recent sync exists
    """
    with current_app.app_context():
        try:
            logger.info(f"[SYNC] Syncing schedule definition {schedule_def_id} (force={force})")
            
            creds_path = current_app.config.get('GOOGLE_APPLICATION_CREDENTIALS', 'service-account-creds.json')
            sync_service = GoogleSheetsSyncService(creds_path)
            
            result = sync_service.sync_schedule_data(
                schedule_def_id=schedule_def_id,
                sync_type='scheduled',
                triggered_by=None,
                force=force
            )
            
            return result
            
        except Exception as e:
            logger.error(f"[SYNC] Error syncing schedule definition {schedule_def_id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise


