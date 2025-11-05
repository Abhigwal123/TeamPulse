"""
Google Sheets Sync Service
Syncs data from Google Sheets to local database cache
Implements exponential backoff for rate limit errors
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import time

from app import db
from app.models import ScheduleDefinition, User, EmployeeMapping, CachedSchedule, SyncLog
from app.services.dashboard_data_service import DashboardDataService
from app.services.google_sheets_import import fetch_schedule_data

logger = logging.getLogger(__name__)

class GoogleSheetsSyncService:
    """Service to sync Google Sheets data to database cache"""
    
    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = credentials_path
    
    def sync_schedule_data(self, schedule_def_id: str, sync_type: str = 'auto', 
                          triggered_by: Optional[str] = None, force: bool = False) -> Dict[str, Any]:
        """
        Sync schedule data from Google Sheets to database
        
        Args:
            schedule_def_id: Schedule definition ID
            sync_type: Type of sync ('auto', 'manual', 'scheduled')
            triggered_by: User ID who triggered sync (for manual syncs)
            force: Force sync even if recent sync exists
            
        Returns:
            Dictionary with sync results
        """
        schedule_def = ScheduleDefinition.query.get(schedule_def_id)
        if not schedule_def:
            return {
                'success': False,
                'error': f'Schedule definition not found: {schedule_def_id}'
            }
        
        # Check if sync is needed
        if not force:
            if not SyncLog.should_sync(schedule_def_id=schedule_def_id, min_minutes=10):
                last_sync = SyncLog.get_last_sync(schedule_def_id=schedule_def_id)
                return {
                    'success': True,
                    'skipped': True,
                    'message': f'Data is fresh. Last synced: {last_sync.completed_at.isoformat() if last_sync and last_sync.completed_at else "Never"}',
                    'last_synced_at': last_sync.completed_at.isoformat() if last_sync and last_sync.completed_at else None
                }
        
        # Create sync log
        sync_log = SyncLog.create_sync_log(
            schedule_def_id=schedule_def_id,
            tenant_id=schedule_def.tenantID,
            sync_type=sync_type,
            triggered_by=triggered_by
        )
        
        try:
            logger.info(f"[SYNC] Starting sync for schedule {schedule_def_id} (type: {sync_type})")
            
            # Fetch data from Google Sheets with retry logic
            sheets_data = self._fetch_with_retry(schedule_def_id)
            
            if not sheets_data.get('success'):
                error_msg = sheets_data.get('error', 'Unknown error')
                sync_log.mark_completed(rows_synced=0, users_synced=0, error_message=error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
            
            # Parse and store schedule data
            rows_synced, users_synced = self._store_schedule_data(schedule_def_id, sheets_data)
            
            # Mark sync as completed
            sync_log.mark_completed(rows_synced=rows_synced, users_synced=users_synced)
            
            logger.info(f"[SYNC] Google Sheets -> Database success: {rows_synced} rows, {users_synced} users")
            
            return {
                'success': True,
                'rows_synced': rows_synced,
                'users_synced': users_synced,
                'last_synced_at': sync_log.completed_at.isoformat() if sync_log.completed_at else None,
                'sync_log_id': sync_log.id
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[SYNC] Sync failed: {error_msg}")
            import traceback
            logger.error(traceback.format_exc())
            
            sync_log.mark_completed(rows_synced=0, users_synced=0, error_message=error_msg)
            
            return {
                'success': False,
                'error': error_msg
            }
    
    def _fetch_with_retry(self, schedule_def_id: str, max_retries: int = 3, 
                          initial_delay: float = 2.0) -> Dict[str, Any]:
        """
        Fetch schedule data with exponential backoff retry
        
        Args:
            schedule_def_id: Schedule definition ID
            max_retries: Maximum retry attempts
            initial_delay: Initial delay in seconds
            
        Returns:
            Dictionary with fetched data
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"[SYNC] Fetching from Google Sheets API (attempt {attempt + 1}/{max_retries})")
                sheets_data = fetch_schedule_data(
                    schedule_def_id,
                    self.credentials_path,
                    user_role="employee"
                )
                
                if sheets_data.get('success'):
                    return sheets_data
                
                # Check if it's a rate limit error
                error = sheets_data.get('error', '')
                if '429' in str(error) or 'quota' in str(error).lower() or 'rate limit' in str(error).lower():
                    if attempt < max_retries - 1:
                        delay = initial_delay * (2 ** attempt)
                        logger.warning(f"[SYNC] Rate limit error (429), retrying in {delay:.1f}s...")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"[SYNC] Rate limit error after {max_retries} retries")
                        return sheets_data
                
                # For other errors, return immediately
                return sheets_data
                
            except Exception as e:
                error_msg = str(e)
                if attempt < max_retries - 1 and ('429' in error_msg or 'quota' in error_msg.lower()):
                    delay = initial_delay * (2 ** attempt)
                    logger.warning(f"[SYNC] Error: {error_msg}, retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"[SYNC] Fetch failed: {error_msg}")
                    return {
                        'success': False,
                        'error': error_msg
                    }
        
        return {
            'success': False,
            'error': 'Failed to fetch after retries'
        }
    
    def _store_schedule_data(self, schedule_def_id: str, sheets_data: Dict[str, Any]) -> tuple:
        """
        Parse and store schedule data in database
        
        Args:
            schedule_def_id: Schedule definition ID
            sheets_data: Data from Google Sheets
            
        Returns:
            Tuple of (rows_synced, users_synced)
        """
        rows_synced = 0
        users_synced = 0
        
        sheets = sheets_data.get('sheets', {})
        final_output = sheets.get('final_output', {})
        
        if not final_output.get('success'):
            logger.warning(f"[SYNC] Final output sheet not available")
            return rows_synced, users_synced
        
        output_data = final_output.get('data', [])
        output_columns = final_output.get('columns', [])
        
        if not output_data or not output_columns:
            logger.warning(f"[SYNC] No data in final output sheet")
            return rows_synced, users_synced
        
        # Get all users with employee mappings for this schedule
        employee_mappings = EmployeeMapping.query.filter_by(
            schedule_def_id=schedule_def_id,
            is_active=True
        ).all()
        
        # Create a mapping of sheets_identifier -> user_id
        identifier_to_user = {}
        for mapping in employee_mappings:
            identifier_to_user[mapping.sheets_identifier] = mapping.userID
            if mapping.sheets_name_id:
                # Also map the full name/ID format
                identifier_to_user[mapping.sheets_name_id] = mapping.userID
                # Map parts if it contains '/'
                if '/' in mapping.sheets_name_id:
                    for part in mapping.sheets_name_id.split('/'):
                        if part.strip():
                            identifier_to_user[part.strip()] = mapping.userID
        
        logger.info(f"[SYNC] Found {len(employee_mappings)} employee mappings")
        
        # Find the employee identifier column
        identifier_column = None
        for col in ['員工(姓名/ID)', '員工姓名/ID', '員工', 'username', 'employee_id', 'name']:
            if col in output_columns:
                identifier_column = col
                break
        
        if not identifier_column:
            logger.warning(f"[SYNC] Could not find identifier column in: {output_columns[:5]}")
            return rows_synced, users_synced
        
        # Process each row
        synced_users = set()
        
        for row in output_data:
            if not isinstance(row, dict):
                continue
            
            # Get employee identifier
            identifier = row.get(identifier_column, '')
            if not identifier:
                continue
            
            # Find matching user
            user_id = None
            identifier_str = str(identifier).strip()
            
            # Try exact match first
            if identifier_str in identifier_to_user:
                user_id = identifier_to_user[identifier_str]
            else:
                # Try partial match
                for key, uid in identifier_to_user.items():
                    if identifier_str in str(key) or str(key) in identifier_str:
                        user_id = uid
                        break
            
            if not user_id:
                # Skip rows without user mapping
                continue
            
            synced_users.add(user_id)
            
            # Process date columns (skip identifier column)
            date_columns = [col for col in output_columns if col != identifier_column]
            
            # Clear existing data for this user first
            CachedSchedule.clear_user_schedule(user_id, schedule_def_id)
            
            # Process each date column
            for date_col in date_columns:
                try:
                    # Parse date from column header
                    date_obj = self._parse_date(date_col)
                    if not date_obj:
                        continue
                    
                    # Get shift value
                    shift_value = row.get(date_col, '')
                    if shift_value is None:
                        continue
                    shift_value = str(shift_value).strip()
                    if not shift_value or shift_value == '' or shift_value.upper() == 'NULL':
                        continue
                    
                    # Normalize shift type
                    shift_type = self._normalize_shift_type(shift_value)
                    time_range = self._get_time_range(shift_type)
                    
                    # Store in database
                    schedule_entry = CachedSchedule(
                        schedule_def_id=schedule_def_id,
                        user_id=user_id,
                        date=date_obj,
                        shift_type=shift_type,
                        time_range=time_range
                    )
                    
                    db.session.merge(schedule_entry)
                    rows_synced += 1
                    
                except Exception as e:
                    logger.warning(f"[SYNC] Error processing date column {date_col}: {e}")
                    continue
        
        # Commit all changes
        db.session.commit()
        
        users_synced = len(synced_users)
        logger.info(f"[SYNC] Stored {rows_synced} schedule entries for {users_synced} users")
        
        return rows_synced, users_synced
    
    def _parse_date(self, date_str: str) -> Optional[datetime.date]:
        """Parse date from various formats"""
        if not date_str:
            return None
        
        date_str = str(date_str).strip()
        
        # Try common date formats
        formats = [
            '%Y-%m-%d',      # 2025-11-03
            '%Y/%m/%d',      # 2025/11/03
            '%m/%d/%Y',      # 11/03/2025
            '%Y年%m月%d日',  # 2025年11月03日
        ]
        
        for fmt in formats:
            try:
                parsed = datetime.strptime(date_str, fmt).date()
                return parsed
            except:
                continue
        
        # Try to extract date from string using regex
        import re
        # Match patterns like "2025/10/01" or "2025-10-01"
        match = re.search(r'(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})', date_str)
        if match:
            year, month, day = map(int, match.groups())
            try:
                parsed = datetime(year, month, day).date()
                return parsed
            except ValueError:
                pass
        
        # Try to parse as ISO format
        try:
            parsed = datetime.fromisoformat(date_str.replace('/', '-')).date()
            return parsed
        except:
            pass
        
        return None
    
    def _normalize_shift_type(self, shift_value: str) -> str:
        """Normalize shift type from various formats"""
        if not shift_value:
            return 'OFF'
        
        shift_upper = str(shift_value).upper().strip()
        
        # Check for OFF first
        if shift_upper in ['OFF', '休', '休假', 'NULL', ''] or shift_upper == '':
            return 'OFF'
        
        # Check if it's a complex shift description (e.g., "A 櫃台人力", "B 二線人力")
        # These should be treated as work shifts (D)
        if any(keyword in shift_upper for keyword in ['櫃台', '二線', '藥局', '人力', 'COUNTER', 'DESK', 'PHARMACY']):
            return 'D'  # Treat complex shift descriptions as day shift
        
        # Check for simple shift codes
        if shift_upper in ['E', 'EVENING', '小夜']:
            return 'E'
        elif shift_upper in ['N', 'NIGHT', '大夜']:
            return 'N'
        elif shift_upper in ['D', 'DAY', '白班']:
            return 'D'
        else:
            # Default to D if single letter
            if len(shift_upper) == 1 and shift_upper in ['D', 'E', 'N']:
                return shift_upper
            # For unknown complex values, default to D (work shift)
            return 'D'
    
    def _get_time_range(self, shift_type: str) -> str:
        """Get default time range for shift type"""
        time_ranges = {
            'D': '08:00 - 16:00',
            'E': '16:00 - 00:00',
            'N': '00:00 - 08:00',
            'OFF': '--'
        }
        return time_ranges.get(shift_type, '--')

