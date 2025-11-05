# Schedule Permission Routes
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import SchedulePermission, User, ScheduleDefinition
try:
    from app.schemas import SchedulePermissionSchema, SchedulePermissionUpdateSchema, PaginationSchema
    SCHEMAS_AVAILABLE = True
except ImportError:
    SCHEMAS_AVAILABLE = False
    SchedulePermissionSchema = None
    SchedulePermissionUpdateSchema = None
    PaginationSchema = None
import logging

logger = logging.getLogger(__name__)

schedule_permission_bp = Blueprint('schedule_permissions', __name__)

def get_current_user():
    """Get current authenticated user"""
    current_user_id = get_jwt_identity()
    return User.query.get(current_user_id)

def require_admin_or_scheduler():
    """Decorator to require admin or scheduler role"""
    def decorator(f):
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user or user.role not in ['admin', 'scheduler']:
                return jsonify({'error': 'Admin or scheduler access required'}), 403
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator

@schedule_permission_bp.route('/', methods=['GET', 'OPTIONS'])
@schedule_permission_bp.route('', methods=['GET', 'OPTIONS'])  # Support both / and no slash
@jwt_required()
def get_schedule_permissions():
    """Get schedule permissions for current tenant"""
    import logging
    trace_logger = logging.getLogger('trace')
    
    # Handle CORS preflight
    if request.method == "OPTIONS":
        trace_logger.info("[TRACE] Backend: OPTIONS preflight for /schedule-permissions")
        response = jsonify({})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "GET, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response
    
    trace_logger.info("[TRACE] Backend: GET /schedule-permissions")
    trace_logger.info(f"[TRACE] Backend: Path: {request.path}")
    trace_logger.info(f"[TRACE] Backend: Query params: {dict(request.args)}")
    
    try:
        from flask_jwt_extended import get_jwt_identity, get_jwt
        current_user_id = get_jwt_identity()
        claims = get_jwt() or {}
        trace_logger.info(f"[TRACE] Backend: User ID: {current_user_id}")
        trace_logger.info(f"[TRACE] Backend: Role: {claims.get('role')}")
    except:
        pass
    
    try:
        user = get_current_user()
        if not user:
            response = jsonify({'error': 'User not found'})
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response, 404
        
        # Parse pagination parameters with safe defaults
        try:
            if SCHEMAS_AVAILABLE and PaginationSchema:
                pagination_schema = PaginationSchema()
                pagination_data = pagination_schema.load(request.args)
                page = int(pagination_data.get('page', 1))
                per_page = min(int(pagination_data.get('per_page', 20)), 100)
            else:
                page = int(request.args.get('page', 1) or 1)
                per_page = min(int(request.args.get('per_page', 20) or 20), 100)
        except Exception:
            page = int(request.args.get('page', 1) or 1)
            per_page = min(int(request.args.get('per_page', 20) or 20), 100)
        
        # Query schedule permissions for current tenant
        permissions_query = SchedulePermission.query.filter_by(tenantID=user.tenantID)
        
        # Apply user filter if specified
        user_filter = request.args.get('user_id')
        if user_filter:
            permissions_query = permissions_query.filter_by(userID=user_filter)
        
        # Apply schedule filter if specified
        schedule_filter = request.args.get('schedule_def_id')
        if schedule_filter:
            permissions_query = permissions_query.filter_by(scheduleDefID=schedule_filter)
        
        # Apply active filter if specified
        active_filter = request.args.get('active')
        if active_filter is not None:
            is_active = active_filter.lower() == 'true'
            permissions_query = permissions_query.filter_by(is_active=is_active)
        
        permissions_pagination = permissions_query.order_by(SchedulePermission.created_at.desc()).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        permissions = [perm.to_dict() for perm in permissions_pagination.items]
        
        trace_logger.info(f"[TRACE] Backend: Returning {len(permissions)} permissions")
        trace_logger.info(f"[TRACE] Backend: Response structure: {{success: True, data: [{len(permissions)} items], pagination: {{...}}}}")
        
        response = jsonify({
            'success': True,
            'data': permissions,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': permissions_pagination.total,
                'pages': permissions_pagination.pages,
                'has_next': permissions_pagination.has_next,
                'has_prev': permissions_pagination.has_prev
            }
        })
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 200
        
    except Exception as e:
        logger.error(f"Get schedule permissions error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve schedule permissions', 'details': str(e)}), 500

@schedule_permission_bp.route('/', methods=['POST'])
@jwt_required()
@require_admin_or_scheduler()
def create_schedule_permission():
    """Create a new schedule permission"""
    try:
        current_user = get_current_user()
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate permission data
        permission_schema = SchedulePermissionSchema()
        errors = permission_schema.validate(data)
        if errors:
            return jsonify({'error': 'Invalid permission data', 'details': errors}), 400
        
        # Verify user belongs to tenant
        user = User.query.get(data['userID'])
        if not user or user.tenantID != current_user.tenantID:
            return jsonify({'error': 'Invalid user'}), 400
        
        # Verify schedule definition belongs to tenant
        schedule_def = ScheduleDefinition.query.get(data['scheduleDefID'])
        if not schedule_def or schedule_def.tenantID != current_user.tenantID:
            return jsonify({'error': 'Invalid schedule definition'}), 400
        
        # Check if permission already exists
        existing_perm = SchedulePermission.find_by_user_and_schedule(data['userID'], data['scheduleDefID'])
        if existing_perm:
            return jsonify({'error': 'Permission already exists for this user and schedule'}), 409
        
        # Create permission
        permission = SchedulePermission(
            tenantID=current_user.tenantID,
            userID=data['userID'],
            scheduleDefID=data['scheduleDefID'],
            canRunJob=data['canRunJob'],
            granted_by=current_user.userID,
            expires_at=data.get('expires_at'),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(permission)
        db.session.commit()
        
        logger.info(f"New schedule permission created for user {user.username} and schedule {schedule_def.scheduleName} by {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': 'Schedule permission created successfully',
            'data': permission.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Create schedule permission error: {str(e)}")
        return jsonify({'error': 'Failed to create schedule permission', 'details': str(e)}), 500

@schedule_permission_bp.route('/<permission_id>', methods=['GET'])
@jwt_required()
def get_schedule_permission(permission_id):
    """Get specific schedule permission information"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Find permission
        permission = SchedulePermission.query.get(permission_id)
        if not permission:
            return jsonify({'error': 'Schedule permission not found'}), 404
        
        # Check tenant access
        if user.tenantID != permission.tenantID:
            return jsonify({'error': 'Access denied'}), 403
        
        return jsonify({
            'success': True,
            'data': permission.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Get schedule permission error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve schedule permission', 'details': str(e)}), 500

@schedule_permission_bp.route('/<permission_id>', methods=['PUT'])
@jwt_required()
@require_admin_or_scheduler()
def update_schedule_permission(permission_id):
    """Update schedule permission information"""
    try:
        current_user = get_current_user()
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate update data
        update_schema = SchedulePermissionUpdateSchema()
        errors = update_schema.validate(data)
        if errors:
            return jsonify({'error': 'Invalid update data', 'details': errors}), 400
        
        # Find permission
        permission = SchedulePermission.query.get(permission_id)
        if not permission:
            return jsonify({'error': 'Schedule permission not found'}), 404
        
        # Check tenant access
        if current_user.tenantID != permission.tenantID:
            return jsonify({'error': 'Access denied'}), 403
        
        # Update fields
        if 'canRunJob' in data:
            permission.canRunJob = data['canRunJob']
        
        if 'expires_at' in data:
            permission.expires_at = data['expires_at']
        
        if 'is_active' in data:
            permission.is_active = data['is_active']
        
        permission.updated_at = db.func.now()
        db.session.commit()
        
        logger.info(f"Schedule permission updated: {permission_id} by user: {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': 'Schedule permission updated successfully',
            'data': permission.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Update schedule permission error: {str(e)}")
        return jsonify({'error': 'Failed to update schedule permission', 'details': str(e)}), 500

@schedule_permission_bp.route('/<permission_id>', methods=['DELETE'])
@jwt_required()
@require_admin_or_scheduler()
def delete_schedule_permission(permission_id):
    """Delete schedule permission"""
    try:
        current_user = get_current_user()
        
        # Find permission
        permission = SchedulePermission.query.get(permission_id)
        if not permission:
            return jsonify({'error': 'Schedule permission not found'}), 404
        
        # Check tenant access
        if current_user.tenantID != permission.tenantID:
            return jsonify({'error': 'Access denied'}), 403
        
        # Delete permission
        db.session.delete(permission)
        db.session.commit()
        
        logger.info(f"Schedule permission deleted: {permission_id} by user: {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': 'Schedule permission deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Delete schedule permission error: {str(e)}")
        return jsonify({'error': 'Failed to delete schedule permission', 'details': str(e)}), 500







