# User Routes
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User, Tenant
try:
    from app.schemas import UserSchema, UserUpdateSchema, PaginationSchema
    SCHEMAS_AVAILABLE = True
except ImportError:
    SCHEMAS_AVAILABLE = False
    UserSchema = None
    UserUpdateSchema = None
    PaginationSchema = None
from app.utils.security import sanitize_input
import logging

logger = logging.getLogger(__name__)

user_bp = Blueprint('users', __name__)

def get_current_user():
    """Get current authenticated user"""
    current_user_id = get_jwt_identity()
    return User.query.get(current_user_id)

def require_admin_or_self(user_id=None):
    """Decorator to require admin role or self access"""
    def decorator(f):
        def decorated_function(*args, **kwargs):
            current_user = get_current_user()
            if not current_user:
                return jsonify({'error': 'User not found'}), 404
            
            # Admin can access any user, others can only access themselves
            if not current_user.is_admin() and (not user_id or current_user.userID != user_id):
                return jsonify({'error': 'Access denied'}), 403
            
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator

@user_bp.route('/', methods=['GET', 'OPTIONS'])
@user_bp.route('', methods=['GET', 'OPTIONS'])  # Support both / and no slash
@jwt_required()
def get_users():
    """Get users for current tenant"""
    import logging
    trace_logger = logging.getLogger('trace')
    
    # Handle CORS preflight
    if request.method == "OPTIONS":
        trace_logger.info("[TRACE] Backend: OPTIONS preflight for /users")
        response = jsonify({})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "GET, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response
    
    trace_logger.info("[TRACE] Backend: GET /users")
    trace_logger.info(f"[TRACE] Backend: Path: {request.path}")
    trace_logger.info(f"[TRACE] Backend: Full path: {request.full_path}")
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
        
        # Query users for current tenant
        users_query = User.query.filter_by(tenantID=user.tenantID)
        
        # Apply role filter if specified
        role_filter = request.args.get('role')
        if role_filter:
            users_query = users_query.filter_by(role=role_filter)
        
        # Apply status filter if specified
        status_filter = request.args.get('status')
        if status_filter:
            users_query = users_query.filter_by(status=status_filter)
        
        users_pagination = users_query.order_by(User.created_at.desc()).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        users = [user_obj.to_dict() for user_obj in users_pagination.items]
        
        trace_logger.info(f"[TRACE] Backend: Returning {len(users)} users")
        trace_logger.info(f"[TRACE] Backend: Response structure: {{success: True, data: [{len(users)} items], pagination: {{...}}}}")
        
        response = jsonify({
            'success': True,
            'data': users,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': users_pagination.total,
                'pages': users_pagination.pages,
                'has_next': users_pagination.has_next,
                'has_prev': users_pagination.has_prev
            }
        })
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 200
        
    except Exception as e:
        logger.error(f"Get users error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve users', 'details': str(e)}), 500

@user_bp.route('/', methods=['POST'])
@jwt_required()
def create_user():
    """Create a new user (admin only)"""
    try:
        current_user = get_current_user()
        if not current_user or not current_user.is_admin():
            return jsonify({'error': 'Admin access required'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate user data
        user_schema = UserSchema()
        errors = user_schema.validate(data)
        if errors:
            return jsonify({'error': 'Invalid user data', 'details': errors}), 400
        
        # Sanitize input
        username = sanitize_input(data['username'])
        
        # Check if username already exists
        existing_user = User.find_by_username(username)
        if existing_user:
            return jsonify({'error': 'Username already exists'}), 409
        
        # Create user
        user = User(
            tenantID=current_user.tenantID,
            username=username,
            password=data['password'],
            role=data['role'],
            status=data.get('status', 'active'),
            email=data.get('email'),
            full_name=data.get('full_name')
        )
        
        db.session.add(user)
        db.session.commit()
        
        logger.info(f"New user created: {user.username} by admin: {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': 'User created successfully',
            'data': user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Create user error: {str(e)}")
        return jsonify({'error': 'Failed to create user', 'details': str(e)}), 500

@user_bp.route('/<user_id>', methods=['GET'])
@jwt_required()
@require_admin_or_self()
def get_user(user_id):
    """Get specific user information"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        current_user = get_current_user()
        
        # Check access permissions
        if not current_user.is_admin() and current_user.tenantID != user.tenantID:
            return jsonify({'error': 'Access denied'}), 403
        
        return jsonify({
            'success': True,
            'data': user.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Get user error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve user', 'details': str(e)}), 500

@user_bp.route('/<user_id>', methods=['PUT'])
@jwt_required()
@require_admin_or_self()
def update_user(user_id):
    """Update user information"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate update data
        update_schema = UserUpdateSchema()
        errors = update_schema.validate(data)
        if errors:
            return jsonify({'error': 'Invalid update data', 'details': errors}), 400
        
        # Find user
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        current_user = get_current_user()
        
        # Check access permissions
        if not current_user.is_admin() and current_user.tenantID != user.tenantID:
            return jsonify({'error': 'Access denied'}), 403
        
        # Update fields
        if 'username' in data:
            username = sanitize_input(data['username'])
            
            # Check if new username conflicts
            existing_user = User.find_by_username(username)
            if existing_user and existing_user.userID != user_id:
                return jsonify({'error': 'Username already exists'}), 409
            
            user.username = username
        
        if 'role' in data and current_user.is_admin():
            user.role = data['role']
        
        if 'status' in data and current_user.is_admin():
            user.status = data['status']
        
        if 'email' in data:
            user.email = data['email']
        
        if 'full_name' in data:
            user.full_name = data['full_name']
        
        user.updated_at = db.func.now()
        db.session.commit()
        
        logger.info(f"User updated: {user.username} by user: {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': 'User updated successfully',
            'data': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Update user error: {str(e)}")
        return jsonify({'error': 'Failed to update user', 'details': str(e)}), 500

@user_bp.route('/<user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """Delete user (admin only)"""
    try:
        current_user = get_current_user()
        if not current_user or not current_user.is_admin():
            return jsonify({'error': 'Admin access required'}), 403
        
        # Find user
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check tenant access
        if current_user.tenantID != user.tenantID:
            return jsonify({'error': 'Access denied'}), 403
        
        # Soft delete (deactivate)
        user.status = 'inactive'
        user.updated_at = db.func.now()
        db.session.commit()
        
        logger.info(f"User deactivated: {user.username} by admin: {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': 'User deactivated successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Delete user error: {str(e)}")
        return jsonify({'error': 'Failed to delete user', 'details': str(e)}), 500







