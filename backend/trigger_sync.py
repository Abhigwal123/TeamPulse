"""
Script to trigger initial Google Sheets sync
Run this to populate the database cache for the first time
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import ScheduleDefinition
from app.services.google_sheets_sync_service import GoogleSheetsSyncService

def main():
    app = create_app()
    with app.app_context():
        # Get all active schedules
        schedules = ScheduleDefinition.query.filter_by(is_active=True).all()
        
        if not schedules:
            print("No active schedules found")
            return
        
        creds_path = app.config.get('GOOGLE_APPLICATION_CREDENTIALS', 'service-account-creds.json')
        sync_service = GoogleSheetsSyncService(creds_path)
        
        for schedule_def in schedules:
            print(f"Syncing schedule: {schedule_def.scheduleName} (ID: {schedule_def.scheduleDefID})")
            result = sync_service.sync_schedule_data(
                schedule_def_id=schedule_def.scheduleDefID,
                sync_type='manual',
                triggered_by=None,
                force=True  # Force sync even if recent
            )
            
            if result.get('success'):
                print(f"✅ Success: Synced {result.get('rows_synced', 0)} rows for {result.get('users_synced', 0)} users")
            else:
                print(f"❌ Failed: {result.get('error', 'Unknown error')}")

if __name__ == '__main__':
    main()


