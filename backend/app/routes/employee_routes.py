from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User
import logging
import os

logger = logging.getLogger(__name__)
employee_bp = Blueprint("employee", __name__)


@employee_bp.route("/schedule", methods=["GET", "OPTIONS"], strict_slashes=False)
def my_schedule():
    """Get schedule for current employee from database cache"""
    logger.info(f"[CACHE] ===== /employee/schedule ENDPOINT CALLED =====")
    logger.info(f"[CACHE] Request method: {request.method}")
    logger.info(f"[CACHE] Request path: {request.path}")
    logger.info(f"[CACHE] Request args: {dict(request.args)}")
    
    # Handle CORS preflight BEFORE JWT check
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "GET, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response
    
    # JWT required for actual GET request
    from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
    verify_jwt_in_request()
    
    try:
        current_user_id = get_jwt_identity()
        logger.info(f"[CACHE] Current user ID from JWT: {current_user_id}")
        
        user = User.query.get(current_user_id)
        
        if not user:
            logger.error(f"[CACHE] User not found for ID: {current_user_id}")
            response = jsonify({'error': 'User not found'})
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response, 404
        
        month = request.args.get('month')
        logger.info(f"[CACHE] ===== START CACHE FETCH =====")
        logger.info(f"[CACHE] Fetching schedule from DB for user {user.userID} (username: {user.username}), month: {month}")
        
        # Get active schedule definition for user's tenant
        from app.models import ScheduleDefinition
        schedule_def = ScheduleDefinition.query.filter_by(
            tenantID=user.tenantID,
            is_active=True
        ).first()
        
        if not schedule_def:
            response = jsonify({
                "success": True,
                "user_id": user.userID,
                "month": month,
                "schedule": [],
                "source": "database",
                "message": "No active schedule found"
            })
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response, 200
        
        # Get cached schedule from database
        from app.models import CachedSchedule, SyncLog
        
        logger.info(f"[CACHE] Querying cache for user_id={current_user_id}, schedule_def_id={schedule_def.scheduleDefID}, month={month}")
        
        schedules_query = CachedSchedule.get_user_schedule(
            user_id=current_user_id,
            schedule_def_id=schedule_def.scheduleDefID,
            month=month,
            max_age_hours=0  # Disable TTL for now - use all cached data
        )
        
        schedules_result = schedules_query.all()
        logger.info(f"[CACHE] Query returned {len(schedules_result)} schedule entries")
        
        schedules = []
        for schedule_entry in schedules_result:
            schedules.append({
                "date": schedule_entry.date.isoformat() if schedule_entry.date else None,
                "shift_type": schedule_entry.shift_type,
                "shiftType": schedule_entry.shift_type,  # Frontend expects camelCase
                "time_range": schedule_entry.time_range,
                "timeRange": schedule_entry.time_range  # Frontend expects camelCase
            })
        
        # Get last sync time
        last_sync = SyncLog.get_last_sync(schedule_def_id=schedule_def.scheduleDefID)
        last_synced_at = last_sync.completed_at.isoformat() if last_sync and last_sync.completed_at else None
        
        logger.info(f"[CACHE] Served {len(schedules)} schedule entries from DB for user {user.userID} (month: {month})")
        
        if len(schedules) == 0:
            logger.warning(f"[CACHE] WARNING: No cached schedules found for user {user.userID}, schedule_def {schedule_def.scheduleDefID}, month {month}")
            # Check if there's any data for this user at all
            all_count = CachedSchedule.query.filter_by(
                user_id=current_user_id,
                schedule_def_id=schedule_def.scheduleDefID
            ).count()
            logger.info(f"[CACHE] Total cached entries for this user/schedule: {all_count}")
        
        response_data = {
            "success": True,
            "user_id": user.userID,
            "month": month,
            "schedule": schedules,
            "source": "database",
            "last_synced_at": last_synced_at,
            "cache_count": len(schedules)
        }
        
        response = jsonify(response_data)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 200
        
    except Exception as e:
        logger.error(f"Error fetching employee schedule: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        response = jsonify({'error': 'Failed to fetch schedule', 'details': str(e)})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 500


@employee_bp.route("/schedule-data", methods=["GET", "OPTIONS"])
def schedule_data():
    """E1 My Dashboard - Employee schedule data: Try cache first, fallback to Google Sheets"""
    # Handle CORS preflight BEFORE JWT check
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "GET, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response
    
    # JWT required for actual GET request
    from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
    from flask import current_app
    from app.models import ScheduleDefinition, CachedSchedule, SyncLog, EmployeeMapping
    
    verify_jwt_in_request()
    
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            response = jsonify({'error': 'User not found'})
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response, 404
        
        logger.info(f"[CACHE] /schedule-data endpoint: Checking cache first for user {user.userID}")
        
        # Get active schedule definition
        schedule_def_id = request.args.get('schedule_def_id')
        if not schedule_def_id:
            schedule_def = ScheduleDefinition.query.filter_by(
                tenantID=user.tenantID,
                is_active=True
            ).first()
            if schedule_def:
                schedule_def_id = schedule_def.scheduleDefID
        
        # Try to get cached data first
        if schedule_def_id:
            try:
                # Get month from request if available
                month = request.args.get('month')
                
                # Get cached schedules
                schedules_query = CachedSchedule.query.filter_by(
                    user_id=current_user_id,
                    schedule_def_id=schedule_def_id
                )
                
                if month:
                    # Parse month format (e.g., "2025-10" or "2025/10")
                    from datetime import datetime
                    try:
                        if '-' in month:
                            year, month_num = map(int, month.split('-'))
                        elif '/' in month:
                            year, month_num = map(int, month.split('/'))
                        else:
                            year, month_num = int(month[:4]), int(month[4:6])
                        
                        # Filter by month using date range
                        from calendar import monthrange
                        from datetime import date
                        _, last_day = monthrange(year, month_num)
                        start_date = date(year, month_num, 1)
                        end_date = date(year, month_num, last_day)
                        
                        schedules_query = schedules_query.filter(
                            CachedSchedule.date >= start_date,
                            CachedSchedule.date <= end_date
                        )
                    except:
                        pass  # If month parsing fails, return all
                
                cached_schedules = schedules_query.all()
                
                if cached_schedules:
                    logger.info(f"[CACHE] Found {len(cached_schedules)} cached entries, returning from DB")
                    
                    # Transform to DashboardDataService format
                    rows = []
                    columns = ['日期', '星期', '班別', '時段']
                    
                    for schedule in cached_schedules:
                        if schedule.date:
                            from datetime import datetime, date as date_type
                            if isinstance(schedule.date, date_type):
                                date_obj = schedule.date
                            elif isinstance(schedule.date, datetime):
                                date_obj = schedule.date.date()
                            else:
                                date_obj = datetime.strptime(str(schedule.date), '%Y-%m-%d').date()
                            
                            # Get day of week
                            weekdays = ['週一', '週二', '週三', '週四', '週五', '週六', '週日']
                            weekday = weekdays[date_obj.weekday()]
                            
                            rows.append({
                                '日期': date_obj.strftime('%Y-%m-%d'),
                                '星期': weekday,
                                '班別': schedule.shift_type or 'D',
                                '時段': schedule.time_range or '--'
                            })
                    
                    # Return cached data
                    dashboard_data = {
                        'success': True,
                        'source': 'database_cache',
                        'data': {
                            'my_schedule': {
                                'rows': rows,
                                'columns': columns
                            }
                        }
                    }
                    
                    # Get last sync time
                    last_sync = SyncLog.get_last_sync(schedule_def_id=schedule_def_id)
                    if last_sync and last_sync.completed_at:
                        dashboard_data['last_synced_at'] = last_sync.completed_at.isoformat()
                    
                    response = jsonify(dashboard_data)
                    response.headers.add("Access-Control-Allow-Origin", "*")
                    return response, 200
                    
            except Exception as cache_err:
                logger.warning(f"[CACHE] Error reading from cache: {cache_err}, falling back to Google Sheets")
        
        # Cache miss or error - try Google Sheets (only if quota allows)
        logger.info(f"[CACHE] Cache miss or empty, attempting Google Sheets fetch")
        
        # Check Google Sheets service availability
        from app.services.google_sheets_import import _try_import_google_sheets
        import app.services.google_sheets_import as sheets_import_module
        
        if not sheets_import_module.SHEETS_AVAILABLE:
            logger.warning("[TRACE] SHEETS_AVAILABLE is False, attempting force retry...")
            success, path = _try_import_google_sheets(force_retry=True)
            import importlib
            importlib.reload(sheets_import_module)
            if not sheets_import_module.SHEETS_AVAILABLE:
                # Return empty data if Sheets unavailable and no cache
                logger.error(f"[CACHE] Google Sheets unavailable and no cache found")
                error_response = {
                    'success': False,
                    'error': 'Google Sheets service not available and no cached data found.',
                    'source': 'none',
                    'data': {
                        'my_schedule': {'rows': [], 'columns': []}
                    }
                }
                response = jsonify(error_response)
                response.headers.add("Access-Control-Allow-Origin", "*")
                return response, 503
        
        # Get credentials path
        creds_path = current_app.config.get('GOOGLE_APPLICATION_CREDENTIALS', 'service-account-creds.json')
        if not os.path.isabs(creds_path) and not os.path.exists(creds_path):
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            project_root = os.path.dirname(backend_dir)
            project_creds = os.path.join(project_root, 'service-account-creds.json')
            if os.path.exists(project_creds):
                creds_path = project_creds
        
        # Try to fetch from Google Sheets
        try:
            from app.services.dashboard_data_service import DashboardDataService
            service = DashboardDataService(creds_path)
            dashboard_data = service.get_employee_dashboard_data(current_user_id, schedule_def_id)
            
            # If successful, update cache in background
            if dashboard_data.get("success"):
                try:
                    # Trigger background cache update
                    import threading
                    def update_cache():
                        try:
                            from app.services.google_sheets_sync_service import GoogleSheetsSyncService
                            sync_service = GoogleSheetsSyncService(creds_path)
                            if schedule_def_id:
                                sync_service.sync_schedule_data(
                                    schedule_def_id=schedule_def_id,
                                    sync_type='auto',
                                    triggered_by=None,
                                    force=False
                                )
                        except Exception as e:
                            logger.warning(f"[CACHE] Background cache update failed: {e}")
                    threading.Thread(target=update_cache, daemon=True).start()
                except:
                    pass
            
            # Return Google Sheets data
            if dashboard_data.get("success"):
                dashboard_data['source'] = 'google_sheets'
                response = jsonify(dashboard_data)
                response.headers.add("Access-Control-Allow-Origin", "*")
                return response, 200
            else:
                # Google Sheets failed - try to return cache anyway (even if empty)
                logger.warning(f"[CACHE] Google Sheets fetch failed, returning empty result")
                error_response = {
                    'success': False,
                    'error': dashboard_data.get('error', 'Failed to fetch from Google Sheets'),
                    'source': 'google_sheets_failed',
                    'data': {
                        'my_schedule': {'rows': [], 'columns': []}
                    }
                }
                response = jsonify(error_response)
                response.headers.add("Access-Control-Allow-Origin", "*")
                return response, 400
                
        except Exception as sheets_err:
            logger.error(f"[CACHE] Google Sheets error (likely rate limit): {sheets_err}")
            # Return empty result - frontend should handle gracefully
            error_response = {
                'success': False,
                'error': f'Google Sheets API error: {str(sheets_err)}',
                'source': 'google_sheets_error',
                'data': {
                    'my_schedule': {'rows': [], 'columns': []}
                }
            }
            response = jsonify(error_response)
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response, 429 if '429' in str(sheets_err) or 'quota' in str(sheets_err).lower() else 500
            
    except Exception as e:
        logger.error(f"Error in schedule-data endpoint: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        response = jsonify({'error': 'Failed to fetch schedule data', 'details': str(e)})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 500


