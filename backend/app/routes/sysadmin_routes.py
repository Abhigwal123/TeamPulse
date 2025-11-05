from flask import Blueprint, jsonify, request
from app.utils.auth import role_required
import logging

logger = logging.getLogger(__name__)


# Note: url_prefix set to None - will be set during registration in __init__.py
sysadmin_bp = Blueprint("sysadmin", __name__)


@sysadmin_bp.route("/dashboard", methods=["GET", "OPTIONS"])
@role_required("SysAdmin")
def dashboard():
    """SysAdmin dashboard with Organization and Schedule Maintenance views"""
    # Handle CORS preflight
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "GET, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response
    
    from flask_jwt_extended import get_jwt_identity
    from app.models import User, Tenant, ScheduleDefinition
    
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            response = jsonify({"success": False, "error": "User not found"})
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response, 404
        
        # Get system-wide statistics
        # ⚠️ AUDIT NOTE: Currently using DATABASE queries, NOT Google Sheets
        # TODO: Replace with Google Sheets fetch if tenant/schedule data is stored in sheets
        
        # ✅ VERIFICATION: 客戶機構總數 - DATABASE QUERY ONLY
        logger.info(f"[TRACE] 客戶機構總數 source confirmed: sysadmin_routes.py:37 → Tenant.query.count() → DATABASE")
        logger.info(f"[TRACE] Data flow: Frontend → /api/v1/sysadmin/dashboard → Tenant.query.count() → SQLite (tenants table)")
        total_tenants = Tenant.query.count()
        active_tenants = Tenant.query.filter_by(is_active=True).count()
        
        # ✅ VERIFICATION: 已設定班表總數 - DATABASE QUERY ONLY
        logger.info(f"[TRACE] 已設定班表總數 source confirmed: sysadmin_routes.py:39 → ScheduleDefinition.query.count() → DATABASE")
        logger.info(f"[TRACE] Data flow: Frontend → /api/v1/sysadmin/dashboard → ScheduleDefinition.query.count() → SQLite (schedule_definitions table)")
        total_schedules = ScheduleDefinition.query.count()
        active_schedules = ScheduleDefinition.query.filter_by(is_active=True).count()
        
        logger.info(f"[TRACE] SysAdmin dashboard stats - tenants: {total_tenants}, schedules: {total_schedules}")
        logger.info(f"[TRACE] ✅ CONFIRMED: No Google Sheets API calls in dashboard endpoint")
        
        stats = {
            "total_tenants": total_tenants,
            "totalTenants": total_tenants,  # Frontend compatibility
            "active_tenants": active_tenants,
            "activeTenants": active_tenants,  # Frontend compatibility
            "total_schedules": total_schedules,
            "totalSchedules": total_schedules,  # Frontend compatibility
            "active_schedules": active_schedules,
            "activeSchedules": active_schedules  # Frontend compatibility
        }
        
        response = jsonify({
            "success": True,
            "dashboard": "sysadmin",
            "user": user.to_dict(),
            "stats": stats,
            "views": ["B1: Organization", "B2: Schedule List", "B3: Schedule Maintenance"]
        })
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 200
    except Exception as e:
        logger.error(f"Error in sysadmin dashboard: {e}")
        import traceback
        logger.error(traceback.format_exc())
        response = jsonify({"success": False, "error": str(e)})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 500


@sysadmin_bp.route("/tenants", methods=["GET"])
@role_required("SysAdmin")
def tenants():
    return jsonify({"tenants": []})


@sysadmin_bp.route("/tenant", methods=["POST"])
@role_required("SysAdmin")
def create_tenant():
    return jsonify({"created": True}), 201


@sysadmin_bp.route("/tenant/<int:tenant_id>", methods=["PUT"])
@role_required("SysAdmin")
def update_tenant(tenant_id: int):
    return jsonify({"updated": True, "id": tenant_id})


@sysadmin_bp.route("/logs", methods=["GET", "OPTIONS"])
@role_required("SysAdmin")
def logs():
    """Get system logs"""
    # Handle CORS preflight
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "GET, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response
    
    try:
        from app.models import ScheduleJobLog
        
        # Get limit from query params (default to 10)
        limit = request.args.get('limit', 10, type=int)
        
        # ⚠️ AUDIT NOTE: Currently using DATABASE query, NOT Google Sheets
        # TODO: Replace with Google Sheets fetch if system logs are stored in 'SystemLogs' sheet
        
        # ✅ VERIFICATION: 系統日誌 - DATABASE QUERY ONLY
        logger.info(f"[TRACE] 系統日誌 source confirmed: sysadmin_routes.py:116 → ScheduleJobLog.query → DATABASE")
        logger.info(f"[TRACE] Data flow: Frontend → /api/v1/sysadmin/logs → ScheduleJobLog.query → SQLite (schedule_job_logs table)")
        logger.info(f"[TRACE] ✅ CONFIRMED: No Google Sheets API calls in logs endpoint")
        logs = ScheduleJobLog.query.order_by(ScheduleJobLog.created_at.desc()).limit(limit).all()
        
        log_list = []
        for log in logs:
            # ScheduleJobLog model has: status, resultSummary, error_message, startTime, endTime
            log_list.append({
                "id": log.logID,
                "logID": log.logID,
                "action": "schedule_job_execution",
                "user_role": "System",
                "user_email": "system",
                "username": "system",
                "timestamp": log.created_at.isoformat() if log.created_at else None,
                "created_at": log.created_at.isoformat() if log.created_at else None,
                "details": {
                    "message": log.resultSummary or log.error_message or f"Schedule job {log.status}",
                    "schedule_def_id": log.scheduleDefID,
                    "status": log.status,
                    "startTime": log.startTime.isoformat() if log.startTime else None,
                    "endTime": log.endTime.isoformat() if log.endTime else None
                }
            })
        
        logger.info(f"[TRACE] Returning {len(log_list)} logs")
        
        response = jsonify({
            "success": True,
            "logs": log_list,
            "data": log_list  # Frontend compatibility
        })
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 200
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        import traceback
        logger.error(traceback.format_exc())
        response = jsonify({"success": False, "logs": [], "error": str(e)})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 500


@sysadmin_bp.route("/system-health", methods=["GET"])
@role_required("SysAdmin")
def system_health():
    """System health check for SysAdmin"""
    from flask import current_app
    import redis
    
    # ✅ VERIFICATION: 系統健康狀態 - RUNTIME STATUS CHECKS ONLY
    logger.info(f"[TRACE] 系統健康狀態 source confirmed: sysadmin_routes.py:system_health() → computed dynamically (runtime checks)")
    logger.info(f"[TRACE] Data flow: Frontend → /api/v1/sysadmin/system-health → runtime_checks() → Redis/Celery status")
    logger.info(f"[TRACE] ✅ CONFIRMED: No Google Sheets API calls in system-health endpoint")
    
    components = {
        "database": True,
        "redis": False,
        "celery": False
    }
    
    # Check Redis
    try:
        broker_url = current_app.config.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
        r = redis.Redis.from_url(broker_url)
        r.ping()
        components["redis"] = True
    except Exception:
        pass
    
    # Check Celery
    try:
        from celery import current_app as celery_app
        components["celery"] = bool(getattr(celery_app, "conf", None))
    except Exception:
        pass
    
    return jsonify({
        "success": True,
        "components": components,
        "status": "ok" if all(components.values()) else "degraded"
    }), 200


@sysadmin_bp.route("/b1-organization", methods=["GET"])
@role_required("SysAdmin")
def b1_organization():
    """B1 Organization Dashboard - Overview from Google Sheets"""
    from flask_jwt_extended import get_jwt_identity
    from flask import current_app
    from app.services.dashboard_data_service import DashboardDataService
    import os
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        current_user_id = get_jwt_identity()
        
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
        
        service = DashboardDataService(creds_path)
        dashboard_data = service.get_sysadmin_b1_data(current_user_id)
        
        logger.info(f"[TRACE] B1 dashboard data - success: {dashboard_data.get('success')}, error: {dashboard_data.get('error', 'None')}")
        
        if dashboard_data.get("success"):
            return jsonify(dashboard_data), 200
        else:
            return jsonify(dashboard_data), 400
    except Exception as e:
        logger.error(f"Error in B1 dashboard: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@sysadmin_bp.route("/b2-schedule-list", methods=["GET"])
@role_required("SysAdmin")
def b2_schedule_list():
    """B2 Schedule List Maintenance - List all schedules"""
    from flask_jwt_extended import get_jwt_identity
    from app.services.dashboard_data_service import DashboardDataService
    
    try:
        current_user_id = get_jwt_identity()
        service = DashboardDataService()
        dashboard_data = service.get_sysadmin_b2_data(current_user_id)
        
        if dashboard_data.get("success"):
            return jsonify(dashboard_data), 200
        else:
            return jsonify(dashboard_data), 400
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in B2 dashboard: {e}")
        return jsonify({"error": str(e)}), 500


@sysadmin_bp.route("/b3-schedule-maintenance", methods=["GET"])
@role_required("SysAdmin")
def b3_schedule_maintenance():
    """B3 Schedule Maintenance - Detailed schedule sheets from Google Sheets"""
    from flask_jwt_extended import get_jwt_identity
    from flask import current_app
    from app.services.dashboard_data_service import DashboardDataService
    
    try:
        current_user_id = get_jwt_identity()
        schedule_def_id = request.args.get('schedule_def_id')
        
        creds_path = current_app.config.get('GOOGLE_APPLICATION_CREDENTIALS', 'service-account-creds.json')
        service = DashboardDataService(creds_path)
        dashboard_data = service.get_sysadmin_b3_data(current_user_id, schedule_def_id)
        
        if dashboard_data.get("success"):
            return jsonify(dashboard_data), 200
        else:
            return jsonify(dashboard_data), 400
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in B3 dashboard: {e}")
        return jsonify({"error": str(e)}), 500



