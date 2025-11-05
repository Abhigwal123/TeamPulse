# Authentication Routes
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from app import db
from app.models import User, Tenant
try:
    from app.schemas import UserSchema, UserLoginSchema, TenantSchema
    SCHEMAS_AVAILABLE = True
except ImportError:
    SCHEMAS_AVAILABLE = False
    UserSchema = None
    UserLoginSchema = None
    TenantSchema = None
from app.utils.security import hash_password, verify_password, validate_password_strength
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

# Blacklist for revoked tokens (in production, use Redis)
blacklisted_tokens = set()

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user
    
    Creates a new user. If no tenant is provided, creates a default tenant.
    Supports both simple user registration and tenant+user registration.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Handle both formats: simple user data or tenant+user data
        if 'user' in data and 'tenant' in data:
            # Full registration with tenant
            tenant_data = data.get('tenant', {})
            user_data = data.get('user', {})
            
            # Validate tenant data if provided
            if tenant_data and SCHEMAS_AVAILABLE and TenantSchema:
                tenant_schema = TenantSchema()
                tenant_errors = tenant_schema.validate(tenant_data)
                if tenant_errors:
                    return jsonify({'error': 'Invalid tenant data', 'details': tenant_errors}), 400
                
                # Check if tenant name already exists
                existing_tenant = Tenant.find_by_name(tenant_data.get('tenantName', ''))
                if existing_tenant:
                    return jsonify({'error': 'Tenant with this name already exists'}), 409
                
                # Create tenant
                tenant = Tenant(
                    tenantName=tenant_data.get('tenantName', 'Default Tenant'),
                    is_active=tenant_data.get('is_active', True)
                )
                db.session.add(tenant)
                db.session.flush()
                tenant_id = tenant.tenantID
            else:
                # Use first available tenant or create default
                tenant = Tenant.query.first()
                if not tenant:
                    tenant = Tenant(tenantName='Default Tenant', is_active=True)
                    db.session.add(tenant)
                    db.session.flush()
                tenant_id = tenant.tenantID
        else:
            # Simple registration - just user data
            user_data = data
            tenant_id = data.get('tenant_id') or data.get('tenantID')
            
            # If no tenant_id provided, use or create default tenant
            if not tenant_id:
                tenant = Tenant.query.first()
                if not tenant:
                    tenant = Tenant(tenantName='Default Tenant', is_active=True)
                    db.session.add(tenant)
                    db.session.flush()
                tenant_id = tenant.tenantID
            else:
                # Verify tenant exists
                tenant = Tenant.query.get(tenant_id)
                if not tenant:
                    return jsonify({'error': 'Tenant not found'}), 404
        
        # Validate user data
        username = user_data.get('username') or data.get('username')
        password = user_data.get('password') or data.get('password')
        email = user_data.get('email') or data.get('email')
        role = user_data.get('role') or data.get('role', 'employee')
        full_name = user_data.get('full_name') or data.get('fullName') or data.get('name')
        
        if not username:
            return jsonify({'error': 'Username is required'}), 400
        if not password:
            return jsonify({'error': 'Password is required'}), 400
        
        # Check if username already exists
        existing_user = User.find_by_username(username)
        if existing_user:
            return jsonify({'error': 'Username already exists'}), 409
        
        # Check if email already exists (if provided)
        if email:
            existing_email = User.find_by_email(email)
            if existing_email:
                return jsonify({'error': 'Email already exists'}), 409
        
        # Create user
        user = User(
            tenantID=tenant_id,
            username=username,
            password=password,
            role=role.lower(),
            status='active',
            email=email,
            full_name=full_name
        )
        db.session.add(user)
        db.session.commit()
        
        # Create access token
        access_token = create_access_token(identity=str(user.userID))
        
        logger.info(f"New user registered: {user.username} in tenant: {tenant.tenantName}")
        
        return jsonify({
            'success': True,
            'message': 'User registered successfully',
            'access_token': access_token,
            'user': user.to_dict(),
            'tenant': tenant.to_dict() if tenant else None
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Registration error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Registration failed', 'details': str(e)}), 500


@auth_bp.route('/register', methods=['GET'])
def register_info():
    """Helpful message when visiting the register URL in a browser."""
    return jsonify({
        'message': 'Use POST to register a new user at this endpoint.',
        'example_body': {
            'username': 'testuser',
            'password': 'password123',
            'email': 'test@example.com',
            'role': 'employee'
        },
        'note': 'You can also send {"tenant": {...}, "user": {...}} to create a tenant and user together.'
    }), 200

@auth_bp.route('/login', methods=['POST', 'OPTIONS'])
def login():
    """
    Authenticate user and return access token
    
    Validates user credentials and returns a JWT token for API access.
    """
    # Handle CORS preflight
    if request.method == "OPTIONS":
        response = jsonify({})
        origin = request.headers.get('Origin', 'http://localhost:5174')
        allowed_origins = [
            "http://localhost:5174",
            "http://localhost:5173",
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:5174",
            "http://127.0.0.1:5173",
        ]
        if origin in allowed_origins or 'localhost:5174' in origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, X-Requested-With"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "3600"
        return response
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate login data
        if SCHEMAS_AVAILABLE and UserLoginSchema:
            login_schema = UserLoginSchema()
            errors = login_schema.validate(data)
            if errors:
                return jsonify({'error': 'Invalid login data', 'details': errors}), 400
        
        username = data['username']
        password = data['password']
        
        # Find user by username - use direct query to avoid relationship loading issues
        user = db.session.query(User).filter_by(username=username).first()
        if not user:
            logger.warning(f"Login attempt with non-existent username: {username}")
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Check if user is active
        if not user.is_active():
            logger.warning(f"Login attempt with inactive user: {username}")
            return jsonify({'error': 'Account is inactive'}), 401
        
        # Verify password
        if not user.check_password(password):
            logger.warning(f"Invalid password for user: {username}")
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Update last login
        user.update_last_login()
        
        # Get tenant info without loading relationship (use direct query)
        tenant = None
        if user.tenantID:
            from app.models import Tenant
            tenant = db.session.query(Tenant).filter_by(tenantID=user.tenantID).first()
        
        # Create access token with role in claims
        additional_claims = {
            'role': user.role,
            'tenantID': user.tenantID,
            'username': user.username
        }
        access_token = create_access_token(identity=str(user.userID), additional_claims=additional_claims)
        
        logger.info(f"User logged in successfully: {username} (role: {user.role})")
        
        response = jsonify({
            'success': True,
            'message': 'Login successful',
            'access_token': access_token,
            'user': user.to_dict(),
            'tenant': tenant.to_dict() if tenant else None
        })
        
        # Add CORS headers explicitly
        origin = request.headers.get('Origin', 'http://localhost:5174')
        allowed_origins = [
            "http://localhost:5174",
            "http://localhost:5173",
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:5174",
            "http://127.0.0.1:5173",
        ]
        if origin in allowed_origins or 'localhost:5174' in origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, X-Requested-With"
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response, 200
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed', 'details': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout user by blacklisting the current token
    
    Adds the current JWT token to a blacklist to prevent further use.
    """
    try:
        jti = get_jwt()['jti']  # JWT ID
        blacklisted_tokens.add(jti)
        
        logger.info(f"User logged out: {get_jwt_identity()}")
        
        return jsonify({
            'success': True,
            'message': 'Logout successful'
        }), 200
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return jsonify({'error': 'Logout failed', 'details': str(e)}), 500

@auth_bp.route('/me', methods=['GET', 'OPTIONS'])
def get_current_user():
    """
    Get current user information
    
    Returns the profile information of the currently authenticated user.
    """
    # Handle CORS preflight - must be BEFORE jwt_required
    if request.method == "OPTIONS":
        response = jsonify({})
        origin = request.headers.get('Origin', 'http://localhost:5174')
        # Only allow specific origins, not wildcard
        allowed_origins = [
            "http://localhost:5174",
            "http://localhost:5173",
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:5174",
            "http://127.0.0.1:5173",
        ]
        if origin in allowed_origins or 'localhost:5174' in origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, X-Requested-With"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "3600"
        return response
    
    # Verify JWT token manually (to avoid decorator blocking OPTIONS)
    from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
    
    try:
        verify_jwt_in_request(optional=False)
        current_user_id = get_jwt_identity()
    except Exception as e:
        # Token invalid or missing - but still return proper CORS headers
        logger.warning(f"JWT verification failed for /auth/me: {str(e)}")
        response = jsonify({'error': 'Authentication required', 'details': str(e)})
        # CORS headers will be added by after_request handler, but add explicitly here too
        origin = request.headers.get('Origin', 'http://localhost:5174')
        allowed_origins = [
            "http://localhost:5174",
            "http://localhost:5173",
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:5174",
            "http://127.0.0.1:5173",
        ]
        if origin in allowed_origins or 'localhost:5174' in origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, X-Requested-With"
            response.headers["Access-Control-Allow-Credentials"] = "true"
        return response, 401
    
    try:
        user = User.query.get(current_user_id)
        
        if not user:
            response = jsonify({'error': 'User not found'})
            origin = request.headers.get('Origin', 'http://localhost:5174')
            allowed_origins = [
                "http://localhost:5174",
                "http://localhost:5173",
                "http://localhost:3000",
                "http://localhost:3001",
                "http://127.0.0.1:5174",
                "http://127.0.0.1:5173",
            ]
            if origin in allowed_origins or 'localhost:5174' in origin:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
            return response, 404
        
        if not user.is_active():
            response = jsonify({'error': 'Account is inactive'})
            origin = request.headers.get('Origin', 'http://localhost:5174')
            allowed_origins = [
                "http://localhost:5174",
                "http://localhost:5173",
                "http://localhost:3000",
                "http://localhost:3001",
                "http://127.0.0.1:5174",
                "http://127.0.0.1:5173",
            ]
            if origin in allowed_origins or 'localhost:5174' in origin:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
            return response, 401
        
        response = jsonify({
            'success': True,
            'user': user.to_dict(),
            'tenant': user.tenant.to_dict() if user.tenant else None
        })
        # Add CORS headers explicitly
        origin = request.headers.get('Origin', 'http://localhost:5174')
        allowed_origins = [
            "http://localhost:5174",
            "http://localhost:5173",
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:5174",
            "http://127.0.0.1:5173",
        ]
        if origin in allowed_origins or 'localhost:5174' in origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, X-Requested-With"
            response.headers["Access-Control-Allow-Credentials"] = "true"
        return response, 200
        
    except Exception as e:
        logger.error(f"Get current user error: {str(e)}")
        response = jsonify({'error': 'Failed to get user information', 'details': str(e)})
        origin = request.headers.get('Origin', 'http://localhost:5174')
        allowed_origins = [
            "http://localhost:5174",
            "http://localhost:5173",
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:5174",
            "http://127.0.0.1:5173",
        ]
        if origin in allowed_origins or 'localhost:5174' in origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        return response, 500

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """
    Change user password
    
    Allows authenticated users to change their password.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'error': 'Current password and new password are required'}), 400
        
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Verify current password
        if not user.check_password(current_password):
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Validate new password strength
        is_valid, error_message = validate_password_strength(new_password)
        if not is_valid:
            return jsonify({'error': error_message}), 400
        
        # Set new password
        user.set_password(new_password)
        db.session.commit()
        
        logger.info(f"Password changed for user: {user.username}")
        
        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Change password error: {str(e)}")
        return jsonify({'error': 'Failed to change password', 'details': str(e)}), 500

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required()
def refresh():
    """
    Refresh access token
    
    Creates a new access token for the current user.
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active():
            return jsonify({'error': 'User not found or inactive'}), 401
        
        # Create new access token
        access_token = create_access_token(identity=str(user.userID))
        
        return jsonify({
            'success': True,
            'access_token': access_token
        }), 200
        
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        return jsonify({'error': 'Failed to refresh token', 'details': str(e)}), 500

# JWT token blacklist checker
def check_if_token_revoked(jwt_header, jwt_payload):
    """Check if token is blacklisted"""
    jti = jwt_payload['jti']
    return jti in blacklisted_tokens

# Error handlers
@auth_bp.errorhandler(401)
def unauthorized(error):
    """Handle 401 Unauthorized errors"""
    return jsonify({'error': 'Authentication required'}), 401

@auth_bp.errorhandler(403)
def forbidden(error):
    """Handle 403 Forbidden errors"""
    return jsonify({'error': 'Insufficient permissions'}), 403







