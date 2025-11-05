from flask import Blueprint, jsonify, current_app, redirect, url_for, request
from flask_jwt_extended import jwt_required
import logging

logger = logging.getLogger(__name__)

common_bp = Blueprint("common", __name__)


# Note: Auth routes are now handled by auth_bp in routes/auth.py
# These routes are kept for backwards compatibility only
# They use a simplified login without database validation


@common_bp.route("/health", methods=["GET", "OPTIONS"])
def health():
    # Handle CORS preflight
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "GET, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response
    
    components = {"flask": True}
    # Redis/Celery checks are best-effort to avoid blocking startup
    try:
        import redis  # type: ignore
        url = current_app.config.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
        r = redis.Redis.from_url(url)
        r.ping()
        components["redis"] = True
    except Exception:
        components["redis"] = False
    try:
        from celery import current_app as celery_app  # type: ignore
        # Not a full ping, just ensure app is configured
        components["celery"] = bool(getattr(celery_app, "conf", None))
    except Exception:
        components["celery"] = False
    
    response = jsonify({"status": "ok" if all(components.values()) else "degraded", "components": components})
    # Add CORS headers explicitly
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Methods", "GET, OPTIONS, POST, PUT, DELETE")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
    return response


@common_bp.route("/routes", methods=["GET"])
def list_routes():
    """List all registered routes (useful for debugging 404s)."""
    try:
        rules = []
        for rule in current_app.url_map.iter_rules():
            methods = ",".join(sorted(m for m in rule.methods if m not in {"HEAD", "OPTIONS"}))
            rules.append({
                "endpoint": rule.endpoint,
                "rule": str(rule),
                "methods": methods
            })
        # Sort for stable output
        rules.sort(key=lambda r: (r["rule"], r["methods"]))
        return jsonify({
            "count": len(rules),
            "routes": rules
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@common_bp.route("/login", methods=["GET", "POST"], strict_slashes=False)
def login_redirect():
    """Redirect /api/v1/login to /api/v1/auth/login"""
    return redirect("/api/v1/auth/login", code=301)


@common_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def unified_dashboard():
    """Unified dashboard endpoint that routes to role-specific dashboard"""
    from flask_jwt_extended import get_jwt_identity, get_jwt
    from app.models import User
    from flask import redirect
    
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Get role from JWT claims or user object
        claims = get_jwt() or {}
        role = claims.get('role') or user.role
        
        # Map ERD roles to dashboard endpoints
        role_map = {
            'Client_Admin': '/api/v1/clientadmin/dashboard',
            'ClientAdmin': '/api/v1/clientadmin/dashboard',
            'SysAdmin': '/api/v1/sysadmin/dashboard',
            'Schedule_Manager': '/api/v1/schedulemanager/dashboard',
            'ScheduleManager': '/api/v1/schedulemanager/dashboard',
            'Department_Employee': '/api/v1/employee/schedule',
            'employee': '/api/v1/employee/schedule'
        }
        
        dashboard_url = role_map.get(role)
        if dashboard_url:
            return redirect(dashboard_url, code=302)
        
        # Default: return user info
        return jsonify({
            "message": "No specific dashboard for role",
            "user": user.to_dict(),
            "role": role
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@common_bp.route("/dashboard/stats", methods=["GET"])
@jwt_required()
def dashboard_stats():
    """Dashboard statistics for current user"""
    from flask_jwt_extended import get_jwt_identity
    from app.models import User, ScheduleJobLog, ScheduleDefinition
    
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        stats = {
            "total_jobs": ScheduleJobLog.query.filter_by(tenantID=user.tenantID).count(),
            "active_schedules": ScheduleDefinition.query.filter_by(tenantID=user.tenantID, is_active=True).count(),
            "recent_activity": ScheduleJobLog.query.filter_by(tenantID=user.tenantID).order_by(ScheduleJobLog.startTime.desc()).limit(5).count()
        }
        
        return jsonify({"success": True, "data": stats}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@common_bp.route("/dashboard/activities", methods=["GET"])
@jwt_required()
def dashboard_activities():
    """Recent activities for dashboard"""
    from flask_jwt_extended import get_jwt_identity
    from app.models import User, ScheduleJobLog
    from datetime import datetime, timedelta
    
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        recent_jobs = ScheduleJobLog.query.filter_by(tenantID=user.tenantID).order_by(ScheduleJobLog.startTime.desc()).limit(10).all()
        
        activities = [{
            "id": job.logID,
            "type": "schedule_run",
            "description": f"Schedule job {job.status}",
            "timestamp": job.startTime.isoformat() if job.startTime else None
        } for job in recent_jobs]
        
        return jsonify({"success": True, "data": activities}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@common_bp.route("/dashboard/notifications", methods=["GET"])
@jwt_required()
def dashboard_notifications():
    """Dashboard notifications"""
    from flask_jwt_extended import get_jwt_identity
    from app.models import User
    
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Return empty notifications for now
        return jsonify({"success": True, "data": []}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@common_bp.route("/analytics/schedule-performance", methods=["GET"])
@jwt_required()
def analytics_schedule_performance():
    """Schedule performance analytics"""
    from flask_jwt_extended import get_jwt_identity
    from app.models import User, ScheduleJobLog
    
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        jobs = ScheduleJobLog.query.filter_by(tenantID=user.tenantID).all()
        
        return jsonify({
            "success": True,
            "data": {
                "total_jobs": len(jobs),
                "success_rate": len([j for j in jobs if j.status == "success"]) / max(len(jobs), 1),
                "performance_metrics": []
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@common_bp.route("/analytics/task-trends", methods=["GET"])
@jwt_required()
def analytics_task_trends():
    """Task trends analytics"""
    from flask_jwt_extended import get_jwt_identity
    from app.models import User, ScheduleJobLog
    from datetime import datetime, timedelta
    
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        days = int(request.args.get('days', 7))
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        jobs = ScheduleJobLog.query.filter(
            ScheduleJobLog.tenantID == user.tenantID,
            ScheduleJobLog.startTime >= cutoff
        ).all()
        
        return jsonify({
            "success": True,
            "data": {
                "period_days": days,
                "total_tasks": len(jobs),
                "trends": []
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@common_bp.route("/analytics/department-analytics", methods=["GET"])
@jwt_required()
def analytics_department_analytics():
    """Department analytics (ClientAdmin only)"""
    from flask_jwt_extended import get_jwt_identity
    from app.models import User, Department
    
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        departments = Department.query.filter_by(tenantID=user.tenantID).all()
        
        return jsonify({
            "success": True,
            "data": {
                "departments": len(departments),
                "analytics": []
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@common_bp.route("/analytics/user-activity", methods=["GET"])
@jwt_required()
def analytics_user_activity():
    """User activity analytics (ClientAdmin only)"""
    from flask_jwt_extended import get_jwt_identity
    from app.models import User
    
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify({
            "success": True,
            "data": {
                "total_users": User.query.filter_by(tenantID=user.tenantID).count(),
                "activity": []
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@common_bp.route("/analytics/system-metrics", methods=["GET"])
@jwt_required()
def analytics_system_metrics():
    """System metrics (SysAdmin only)"""
    from flask_jwt_extended import get_jwt_identity
    from app.models import User, Tenant, ScheduleDefinition
    
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify({
            "success": True,
            "data": {
                "total_tenants": Tenant.query.count(),
                "total_schedules": ScheduleDefinition.query.count(),
                "metrics": []
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@common_bp.route("/data/validate-source", methods=["POST"])
@jwt_required()
def data_validate_source():
    """Validate data source (Excel or Google Sheets)"""
    from flask_jwt_extended import get_jwt_identity
    from app.models import User
    
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        data = request.get_json()
        source_type = data.get("source_type", "")
        
        # Basic validation
        valid = source_type in ["excel", "google_sheets"]
        
        return jsonify({
            "success": True,
            "valid": valid,
            "source_type": source_type
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@common_bp.route("/data/employee", methods=["POST"])
@jwt_required()
def data_employee():
    """Get employee data"""
    return jsonify({"success": True, "data": []}), 200


@common_bp.route("/data/demand", methods=["POST"])
@jwt_required()
def data_demand():
    """Get demand data"""
    return jsonify({"success": True, "data": []}), 200


@common_bp.route("/data/rules", methods=["POST"])
@jwt_required()
def data_rules():
    """Get rules data"""
    return jsonify({"success": True, "data": []}), 200


@common_bp.route("/data/all", methods=["POST"])
@jwt_required()
def data_all():
    """Get all data types"""
    return jsonify({
        "success": True,
        "data": {
            "employee": [],
            "demand": [],
            "rules": []
        }
    }), 200


@common_bp.route("/dashboard/chart-data", methods=["GET"])
@jwt_required()
def dashboard_chart_data():
    """Chart data for dashboard"""
    chart_type = request.args.get("type", "performance")
    
    return jsonify({
        "success": True,
        "type": chart_type,
        "data": []
    }), 200


@common_bp.route("/dashboard/system-health", methods=["GET"])
@jwt_required()
def dashboard_system_health():
    """System health check endpoint"""
    from flask import current_app
    import redis
    
    components = {
        "flask": True,
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
    
    status = "ok" if all(components.values()) else "degraded"
    
    return jsonify({
        "status": status,
        "components": components
    }), 200


@common_bp.route("/system/health", methods=["GET"])
def system_health():
    """System health check endpoint (no auth required for monitoring)"""
    from flask import current_app
    import redis
    from app import db
    
    components = {
        "flask": True,
        "database": True,
        "mysql": False,
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

    # Check DB connectivity and mark mysql if applicable
    try:
        db.session.execute(db.text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    components["database"] = db_ok
    try:
        uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
        components["mysql"] = db_ok and ("mysql" in uri.lower())
    except Exception:
        components["mysql"] = False
    
    status = "ok" if all(components.values()) else "degraded"
    
    return jsonify({
        "status": status,
        "components": components
    }), 200


@common_bp.route("/dashboard/schedule-data", methods=["GET"])
@jwt_required()
def dashboard_schedule_data():
    """Dashboard schedule data endpoint (for employees) - redirects to employee schedule-data"""
    from flask_jwt_extended import get_jwt_identity
    from app.models import User
    
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Return employee schedule data
        return jsonify({
            "success": True,
            "data": {
                "user_id": user.userID,
                "schedule": []
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@common_bp.route("/schedule/", methods=["GET"])
@jwt_required()
def schedule_user_tasks():
    """Get employee schedule from database cache (if month param provided) or job logs"""
    from flask_jwt_extended import get_jwt_identity
    from app.models import User, ScheduleJobLog, ScheduleDefinition, CachedSchedule, SyncLog
    
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # If month parameter is provided, return employee schedule from cache
        month = request.args.get('month')
        if month:
            logger.info(f"[CACHE] /schedule/ endpoint: Fetching schedule from DB for user {user.userID}, month: {month}")
            
            # Get active schedule definition
            schedule_def = ScheduleDefinition.query.filter_by(
                tenantID=user.tenantID,
                is_active=True
            ).first()
            
            if not schedule_def:
                return jsonify({
                    "success": True,
                    "month": month,
                    "schedule": [],
                    "source": "database",
                    "message": "No active schedule found"
                }), 200
            
            # Get cached schedule from database
            schedules_query = CachedSchedule.get_user_schedule(
                user_id=current_user_id,
                schedule_def_id=schedule_def.scheduleDefID,
                month=month
            )
            
            schedules = []
            for schedule_entry in schedules_query.all():
                schedules.append({
                    "date": schedule_entry.date.isoformat() if schedule_entry.date else None,
                    "shift_type": schedule_entry.shift_type,
                    "shiftType": schedule_entry.shift_type,  # Also include camelCase for frontend
                    "time_range": schedule_entry.time_range,
                    "timeRange": schedule_entry.time_range  # Also include camelCase
                })
            
            # Get last sync time
            last_sync = SyncLog.get_last_sync(schedule_def_id=schedule_def.scheduleDefID)
            last_synced_at = last_sync.completed_at.isoformat() if last_sync and last_sync.completed_at else None
            
            # If cache is empty and no recent sync, trigger background sync
            if len(schedules) == 0 and (not last_sync or not last_sync.completed_at):
                logger.info(f"[CACHE] Cache empty for month {month}, triggering background sync")
                try:
                    # Trigger async sync (non-blocking)
                    from app.services.google_sheets_sync_service import GoogleSheetsSyncService
                    creds_path = current_app.config.get('GOOGLE_APPLICATION_CREDENTIALS', 'service-account-creds.json')
                    sync_service = GoogleSheetsSyncService(creds_path)
                    # Run sync in background thread (don't wait for it)
                    import threading
                    def sync_in_background():
                        try:
                            sync_service.sync_schedule_data(
                                schedule_def_id=schedule_def.scheduleDefID,
                                sync_type='auto',
                                triggered_by=None,
                                force=False
                            )
                        except Exception as e:
                            logger.error(f"Background sync failed: {e}")
                    threading.Thread(target=sync_in_background, daemon=True).start()
                    logger.info(f"[CACHE] Background sync triggered for schedule {schedule_def.scheduleDefID}")
                except Exception as e:
                    logger.warning(f"[CACHE] Failed to trigger background sync: {e}")
            
            logger.info(f"[CACHE] Served {len(schedules)} schedule entries from DB via /schedule/ endpoint")
            
            return jsonify({
                "success": True,
                "month": month,
                "schedule": schedules,
                "source": "database",
                "last_synced_at": last_synced_at,
                "cache_empty": len(schedules) == 0
            }), 200
        
        # No month parameter - return job logs (backward compatibility)
        tasks = ScheduleJobLog.query.filter_by(
            tenantID=user.tenantID,
            runByUserID=user.userID
        ).order_by(ScheduleJobLog.startTime.desc()).limit(20).all()
        
        return jsonify([task.to_dict() for task in tasks]), 200
    except Exception as e:
        logger.error(f"Error in schedule_user_tasks: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@common_bp.route("/admin/sync", methods=["POST", "OPTIONS"])
@jwt_required()
def sync_google_sheets():
    """Manual sync trigger for Google Sheets to database"""
    from flask_jwt_extended import get_jwt_identity
    from app.utils.auth import role_required
    from app.models import ScheduleDefinition, User, SyncLog
    
    # Handle CORS preflight
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response
    
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            response = jsonify({"success": False, "error": "User not found"})
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response, 404
        
        # Get schedule_def_id from request (optional)
        data = request.get_json() or {}
        schedule_def_id = data.get('schedule_def_id')
        force = data.get('force', False)
        
        # Import sync service
        from flask import current_app
        from app.services.google_sheets_sync_service import GoogleSheetsSyncService
        
        creds_path = current_app.config.get('GOOGLE_APPLICATION_CREDENTIALS', 'service-account-creds.json')
        sync_service = GoogleSheetsSyncService(creds_path)
        
        if schedule_def_id:
            # Sync specific schedule
            result = sync_service.sync_schedule_data(
                schedule_def_id=schedule_def_id,
                sync_type='manual',
                triggered_by=current_user_id,
                force=force
            )
        else:
            # Sync all active schedules for user's tenant
            schedules = ScheduleDefinition.query.filter_by(
                tenantID=user.tenantID,
                is_active=True
            ).all()
            
            results = []
            for schedule_def in schedules:
                sync_result = sync_service.sync_schedule_data(
                    schedule_def_id=schedule_def.scheduleDefID,
                    sync_type='manual',
                    triggered_by=current_user_id,
                    force=force
                )
                results.append({
                    'schedule_def_id': schedule_def.scheduleDefID,
                    'schedule_name': schedule_def.scheduleName,
                    **sync_result
                })
            
            result = {
                'success': all(r.get('success', False) for r in results),
                'schedules': results,
                'total_synced': len([r for r in results if r.get('success', False)])
            }
        
        response = jsonify(result)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 200
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error syncing Google Sheets: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        response = jsonify({"success": False, "error": str(e)})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 500


@common_bp.route("/admin/sync/status", methods=["GET", "OPTIONS"])
@jwt_required()
def sync_status():
    """Get sync status for schedule definitions"""
    from flask_jwt_extended import get_jwt_identity
    from app.models import User, SyncLog
    
    # Handle CORS preflight
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "GET, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response
    
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            response = jsonify({"success": False, "error": "User not found"})
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response, 404
        
        schedule_def_id = request.args.get('schedule_def_id')
        
        if schedule_def_id:
            last_sync = SyncLog.get_last_sync(schedule_def_id=schedule_def_id)
        else:
            last_sync = SyncLog.get_last_sync(tenant_id=user.tenantID)
        
        if last_sync:
            status_data = {
                'last_synced_at': last_sync.completed_at.isoformat() if last_sync.completed_at else None,
                'status': last_sync.status,
                'rows_synced': last_sync.rows_synced,
                'users_synced': last_sync.users_synced,
                'duration_seconds': last_sync.duration_seconds
            }
        else:
            status_data = {
                'last_synced_at': None,
                'status': 'never_synced',
                'rows_synced': 0,
                'users_synced': 0
            }
        
        response = jsonify({
            "success": True,
            **status_data
        })
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 200
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting sync status: {str(e)}")
        response = jsonify({"success": False, "error": str(e)})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 500

