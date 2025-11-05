"""
Schedule API Routes
Provides /api/v1/schedule/ endpoint for fetching employee schedule data
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app import db
from app.models import User
import logging
import time
import os
from app.utils.trace_logger import (
    trace_api_request, trace_sheets_fetch, trace_response, trace_error
)

logger = logging.getLogger(__name__)
schedule_bp = Blueprint("schedule", __name__)


@schedule_bp.route("/", methods=["GET", "OPTIONS"])
def get_schedule():
    """
    GET /api/v1/schedule/?month=YYYY-MM
    
    Fetch schedule data for the authenticated employee
    """
    start_time = time.time()
    
    # Handle CORS preflight
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "GET, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response
    
    # JWT required for actual GET request
    verify_jwt_in_request()
    
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            trace_error('API Request', 'schedule_routes.py', 'User not found')
            response = jsonify({'error': 'User not found'})
            response.headers.add("Access-Control-Allow-Origin", "*")
            trace_response(404, (time.time() - start_time) * 1000, '/api/v1/schedule/')
            return response, 404
        
        month = request.args.get('month')
        
        # Trace API request
        trace_api_request('/api/v1/schedule/', user.userID, {'month': month})
        
        logger.info(f"Fetching schedule for user {user.userID} (username: {user.username}), month: {month}")
        
        # Try to import Google Sheets service
        from app.services.google_sheets_import import _try_import_google_sheets, SHEETS_AVAILABLE, fetch_schedule_data
        from app.services.dashboard_data_service import DashboardDataService
        from flask import current_app
        
        # Force retry import if not available
        if not SHEETS_AVAILABLE:
            logger.warning("Google Sheets service not available, attempting import...")
            success, path = _try_import_google_sheets(force_retry=True)
            if not success:
                trace_error('Sheets Fetch', 'schedule_routes.py', f'Import failed: {path}')
                error_msg = "Google Sheets service not available. Check backend logs for import errors."
                response = jsonify({'success': False, 'error': error_msg})
                response.headers.add("Access-Control-Allow-Origin", "*")
                trace_response(503, (time.time() - start_time) * 1000, '/api/v1/schedule/')
                return response, 503
        
        # Get credentials path - resolve to project root if relative
        creds_path = current_app.config.get('GOOGLE_APPLICATION_CREDENTIALS', 'service-account-creds.json')
        if not os.path.isabs(creds_path) and not os.path.exists(creds_path):
            # Try project root
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            project_root = os.path.dirname(backend_dir)
            project_creds = os.path.join(project_root, 'service-account-creds.json')
            if os.path.exists(project_creds):
                creds_path = project_creds
                logger.info(f"[TRACE] Found credentials at project root: {creds_path}")
        logger.info(f"[TRACE] Using credentials path: {creds_path}")
        logger.info(f"[TRACE] Credentials file exists: {os.path.exists(creds_path)}")
        
        # Get dashboard data service
        logger.info(f"[TRACE] Creating DashboardDataService with creds_path: {creds_path}")
        service = DashboardDataService(creds_path)
        
        logger.info(f"[TRACE] Calling get_employee_dashboard_data for user_id: {current_user_id}")
        dashboard_data = service.get_employee_dashboard_data(current_user_id, None)
        
        logger.info(f"[TRACE] Dashboard data response - success: {dashboard_data.get('success')}, has_data: {bool(dashboard_data.get('data'))}, error: {dashboard_data.get('error', 'None')}")
        
        # Extract schedule data
        # Handle case where dashboard_data might be a dict or list
        logger.info(f"[TRACE] Dashboard data type: {type(dashboard_data)}")
        
        if isinstance(dashboard_data, dict):
            dashboard_success = dashboard_data.get('success', False)
            dashboard_data_obj = dashboard_data.get('data')
            logger.info(f"[TRACE] Dashboard success: {dashboard_success}, has data: {bool(dashboard_data_obj)}")
        else:
            # If it's not a dict, treat as error
            logger.error(f"[TRACE] Unexpected dashboard_data type: {type(dashboard_data)}, value: {str(dashboard_data)[:100]}")
            dashboard_success = False
            dashboard_data_obj = None
        
        if dashboard_success and dashboard_data_obj:
            logger.info(f"[TRACE] Dashboard data has success=True and data exists")
            my_schedule = dashboard_data_obj.get('my_schedule', {})
            rows = my_schedule.get('rows', [])
            columns = my_schedule.get('columns', [])
            
            logger.info(f"[TRACE] Extracted schedule data - rows: {len(rows)}, columns: {len(columns) if columns else 0}")
            if rows:
                logger.info(f"[TRACE] First row sample (first 5 keys): {list(rows[0].keys())[:5] if isinstance(rows[0], dict) else 'Not a dict'}")
                # Log the employee identifier column value if it exists
                if isinstance(rows[0], dict):
                    emp_col_key = '員工(姓名/ID)'
                    if emp_col_key in rows[0]:
                        logger.info(f"[TRACE] Employee identifier in row: '{rows[0][emp_col_key]}'")
            logger.info(f"[TRACE] Column sample (first 10): {columns[:10] if columns else 'No columns'}")
            if columns and month:
                # Find columns matching the month
                matching_cols = [col for col in columns if col and (month in col or month.replace('-', '/') in col)][:5]
                logger.info(f"[TRACE] Columns matching month '{month}': {matching_cols}")
            
            # Filter by month if provided
            schedule_entries = []
            if rows and columns:
                logger.info(f"[TRACE] Processing {len(rows)} rows with month filter: {month}")
                logger.info(f"[TRACE] First row keys (sample): {list(rows[0].keys())[:5] if rows and isinstance(rows[0], dict) else 'No rows'}")
                
                # Get time period helper function
                def get_time_period(shift_type):
                    shift_map = {
                        'D': '08:00 - 17:00',
                        'E': '16:00 - 01:00',
                        'N': '00:00 - 09:00',
                        'OFF': '休假'
                    }
                    return shift_map.get(shift_type.upper(), '08:00 - 17:00')
                
                # First, try to find columns matching the requested month
                matching_columns = []
                month_pattern = None
                if month:
                    # Convert "2025-11" to "2025/11" pattern for matching
                    if '-' in month:
                        parts = month.split('-')
                        if len(parts) == 2:
                            month_pattern = f"{parts[0]}/{int(parts[1])}/"  # "2025/11/"
                            logger.info(f"[TRACE] Month filter pattern: '{month_pattern}' (from '{month}')")
                    else:
                        month_pattern = month
                    
                    # Find all columns matching the month pattern
                    for col in columns:
                        if col and col != 'username' and col != 'employee_id' and col != '員工(姓名/ID)':
                            col_matches = (
                                col.startswith(month) or  # Direct match "2025-11"
                                col.startswith(month_pattern) or  # Pattern match "2025/11/"
                                month_pattern.replace('/', '-') in col or  # Reverse pattern
                                month in col  # Contains month
                            )
                            if col_matches:
                                matching_columns.append(col)
                    
                    logger.info(f"[TRACE] Found {len(matching_columns)} columns matching month '{month}'")
                    if matching_columns:
                        logger.info(f"[TRACE] Sample matching columns: {matching_columns[:3]}")
                
                # If no columns match requested month, try fallback to previous month
                fallback_used = False
                if len(matching_columns) == 0 and month:
                    logger.info(f"[TRACE] No columns found for month '{month}', checking fallback...")
                    logger.warning(f"[TRACE] No columns found for month '{month}', trying fallback to previous month...")
                    try:
                        year, month_num = month.split('-')
                        # Try previous month
                        prev_month_num = int(month_num) - 1
                        if prev_month_num == 0:
                            prev_month_num = 12
                            year = str(int(year) - 1)
                        prev_month_pattern = f"{year}/{prev_month_num:02d}/"  # e.g., "2025/10/"
                        logger.info(f"[TRACE] Trying fallback to previous month pattern: '{prev_month_pattern}'")
                        
                        for col in columns:
                            if col and col != 'username' and col != 'employee_id' and col != '員工(姓名/ID)':
                                if prev_month_pattern in str(col):
                                    matching_columns.append(col)
                        
                        if matching_columns:
                            fallback_used = True
                            logger.info(f"[TRACE] ✅ Fallback found {len(matching_columns)} columns for previous month")
                            logger.info(f"[TRACE] Sample fallback columns: {matching_columns[:3]}")
                    except Exception as fallback_err:
                        logger.warning(f"[TRACE] Fallback logic failed: {fallback_err}")
                
                # If still no columns, use all date columns (show all available data)
                if len(matching_columns) == 0:
                    logger.warning(f"[TRACE] No month-specific columns found, using all date columns")
                    for col in columns:
                        if col and col != 'username' and col != 'employee_id' and col != '員工(姓名/ID)':
                            # Check if it looks like a date column (contains '/' or date pattern)
                            if '/' in str(col) or any(char.isdigit() for char in str(col)):
                                matching_columns.append(col)
                    logger.info(f"[TRACE] Using {len(matching_columns)} date columns (all available)")
                
                # Now process rows with matching columns
                logger.info(f"[TRACE] Processing {len(rows)} rows with {len(matching_columns)} matching columns")
                for row in rows:
                    if isinstance(row, dict):
                        for col in matching_columns:
                            cell_value = row.get(col)
                            # Check if cell has any value (including empty string check)
                            if cell_value is not None and str(cell_value).strip() != '':
                                shift_value = str(cell_value).strip()
                                
                                # Handle complex shift values like "A 櫃台人力" -> extract shift type
                                # Map common patterns to shift types
                                shift_type = None
                                shift_upper = shift_value.upper()
                                
                                if shift_upper in ['OFF', '休', '休假']:
                                    shift_type = 'OFF'
                                elif 'D' in shift_upper or '白' in shift_value:
                                    shift_type = 'D'
                                elif 'E' in shift_upper or '小夜' in shift_value:
                                    shift_type = 'E'
                                elif 'N' in shift_upper or '大夜' in shift_value:
                                    shift_type = 'N'
                                else:
                                    # For complex values like "A 櫃台人力", default to D or use the value as-is
                                    # Check if it's a simple single letter
                                    if len(shift_value) == 1 and shift_value in ['D', 'E', 'N']:
                                        shift_type = shift_value
                                    else:
                                        # Use 'D' as default for complex assignments
                                        shift_type = 'D'
                                
                                schedule_entries.append({
                                    'date': col,
                                    'shift_type': shift_type or 'D',
                                    'shiftType': shift_type or 'D',  # Frontend compatibility
                                    'time_range': get_time_period(shift_type or 'D'),
                                    'timeRange': get_time_period(shift_type or 'D'),  # Frontend compatibility
                                    'assignment': shift_value if shift_type != shift_value else None  # Keep original value for complex assignments
                                })
                    elif isinstance(row, list):
                        # Handle array format
                        for col_idx, col_name in enumerate(matching_columns):
                            col_idx_in_cols = columns.index(col_name) if col_name in columns else -1
                            if col_idx_in_cols >= 0 and col_idx_in_cols < len(row):
                                cell_value = row[col_idx_in_cols]
                                if cell_value and str(cell_value).strip():
                                    shift_value = str(cell_value).strip()
                                    shift_upper = shift_value.upper()
                                    
                                    if shift_upper in ['OFF', '休', '休假']:
                                        shift_type = 'OFF'
                                    elif shift_value in ['D', 'E', 'N']:
                                        shift_type = shift_value
                                    else:
                                        shift_type = 'D'  # Default
                                    
                                    schedule_entries.append({
                                        'date': col_name,
                                        'shift_type': shift_type,
                                        'shiftType': shift_type,
                                        'time_range': get_time_period(shift_type),
                                        'timeRange': get_time_period(shift_type)
                                    })
                
                logger.info(f"[TRACE] Created {len(schedule_entries)} schedule entries after filtering")
                if len(schedule_entries) > 0:
                    logger.info(f"[TRACE] ✅ Sample schedule entry (first): {schedule_entries[0]}")
                    logger.info(f"[TRACE] ✅ Sample schedule entry (last): {schedule_entries[-1]}")
                elif len(matching_columns) > 0:
                    # Debug why entries are empty even though we have matching columns
                    logger.warning(f"[TRACE] ⚠️ No schedule entries created despite having {len(matching_columns)} matching columns")
                    # Check first row for sample values
                    if rows and len(rows) > 0:
                        first_row = rows[0]
                        sample_values = {}
                        non_empty_count = 0
                        for col in matching_columns[:10]:
                            val = first_row.get(col) if isinstance(first_row, dict) else 'N/A'
                            sample_values[col] = val
                            if val and str(val).strip():
                                non_empty_count += 1
                        logger.warning(f"[TRACE] Sample cell values from first row (first 10 columns): {sample_values}")
                        logger.warning(f"[TRACE] Non-empty cells in first 10 columns: {non_empty_count}/10")
            else:
                logger.warning(f"[TRACE] No rows or columns to process - rows: {len(rows) if rows else 0}, columns: {len(columns) if columns else 0}")
            
            # Trace sheets fetch
            trace_sheets_fetch(len(rows), month, success=True)
            
            # Prepare response
            response_data = {
                'success': True,
                'user_id': user.userID,
                'employee': f"EMP-{user.userID}",  # Frontend expects this format
                'month': month,
                'schedule': schedule_entries,
                'metadata': {
                    'total_rows': len(rows) if rows else 0,
                    'total_entries': len(schedule_entries),
                    'month_pattern': month_pattern if 'month_pattern' in locals() else month,
                    'fallback_used': fallback_used if 'fallback_used' in locals() else False
                }
            }
            
            logger.info(f"[DEBUG] ========== SCHEDULE API RESPONSE ==========")
            logger.info(f"[DEBUG] Response Data Structure:")
            logger.info(f"[DEBUG]   - success: {response_data.get('success')}")
            logger.info(f"[DEBUG]   - user_id: {response_data.get('user_id')}")
            logger.info(f"[DEBUG]   - employee: {response_data.get('employee')}")
            logger.info(f"[DEBUG]   - month: {response_data.get('month')}")
            logger.info(f"[DEBUG]   - schedule_entries_count: {len(schedule_entries)}")
            logger.info(f"[DEBUG]   - schedule type: {type(schedule_entries)}")
            if schedule_entries:
                logger.info(f"[DEBUG]   - First entry: {schedule_entries[0]}")
                logger.info(f"[DEBUG]   - Last entry: {schedule_entries[-1]}")
            logger.info(f"[DEBUG]   - metadata: {response_data.get('metadata')}")
            logger.info(f"[DEBUG] ===========================================")
            logger.info(f"[TRACE] Final API response payload: success=True, schedule_entries={len(schedule_entries)}, month={month}")
            
            # If no entries found, add helpful message
            if len(schedule_entries) == 0:
                # Check what months are available
                available_months = set()
                if columns:
                    for col in columns:
                        if '/' in str(col):
                            # Extract month from date column (e.g., "2025/10/01" -> "2025/10")
                            parts = str(col).split('/')
                            if len(parts) >= 2:
                                month_str = f"{parts[0]}/{parts[1]}"
                                available_months.add(month_str)
                
                if available_months:
                    months_list = sorted(list(available_months))
                    response_data['message'] = f"No schedule data for {month}. Available months: {', '.join(months_list)}"
                    response_data['available_months'] = months_list
                    logger.warning(f"[TRACE] No data for {month}. Available months: {months_list}")
                else:
                    response_data['message'] = f"No schedule data for {month}. No date columns found in sheet."
                    logger.warning(f"[TRACE] No data for {month} and no available months detected")
            else:
                logger.info(f"[TRACE] First schedule entry: {schedule_entries[0]}")
            
            # Log the exact JSON being sent
            import json
            json_str = json.dumps(response_data, ensure_ascii=False, default=str)
            logger.info(f"[DEBUG] JSON Response (first 500 chars): {json_str[:500]}")
            logger.info(f"[DEBUG] JSON Response length: {len(json_str)} bytes")
            
            response = jsonify(response_data)
            response.headers.add("Access-Control-Allow-Origin", "*")
            duration_ms = (time.time() - start_time) * 1000
            trace_response(200, duration_ms, '/api/v1/schedule/')
            
            logger.info(f"[DEBUG] ✅ Sending response with status 200, {len(schedule_entries)} entries")
            return response, 200
            
        else:
            error_msg = dashboard_data.get('error', 'Failed to fetch schedule data')
            logger.error(f"[DEBUG] ========== SCHEDULE API ERROR ==========")
            logger.error(f"[DEBUG] Dashboard data success: {dashboard_data.get('success')}")
            logger.error(f"[DEBUG] Dashboard data error: {error_msg}")
            logger.error(f"[DEBUG] Dashboard data keys: {list(dashboard_data.keys())}")
            logger.error(f"[DEBUG] Dashboard data: {dashboard_data}")
            logger.error(f"[DEBUG] ==========================================")
            
            trace_error('Sheets Fetch', 'schedule_routes.py', error_msg)
            trace_sheets_fetch(0, month, success=False)
            
            error_response = {
                'success': False,
                'error': error_msg,
                'schedule': []
            }
            
            logger.info(f"[DEBUG] Error response JSON: {json.dumps(error_response, ensure_ascii=False)}")
            
            response = jsonify(error_response)
            response.headers.add("Access-Control-Allow-Origin", "*")
            duration_ms = (time.time() - start_time) * 1000
            trace_response(400, duration_ms, '/api/v1/schedule/')
            return response, 400
            
    except Exception as e:
        logger.error(f"Error fetching schedule: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        trace_error('API Request', 'schedule_routes.py', str(e))
        
        response = jsonify({
            'success': False,
            'error': f'Failed to fetch schedule: {str(e)}',
            'schedule': []
        })
        response.headers.add("Access-Control-Allow-Origin", "*")
        duration_ms = (time.time() - start_time) * 1000
        trace_response(500, duration_ms, '/api/v1/schedule/')
        return response, 500

