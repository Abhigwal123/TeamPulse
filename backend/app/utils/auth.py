from functools import wraps
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt


def role_required(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        @jwt_required(optional=True)
        def wrapper(*args, **kwargs):
            # Skip auth check for OPTIONS requests (CORS preflight)
            from flask import request
            if request.method == "OPTIONS":
                return fn(*args, **kwargs)
            
            claims = get_jwt() or {}
            role = claims.get("role")
            if allowed_roles and role not in allowed_roles:
                return jsonify({"error": "forbidden", "reason": "insufficient_role"}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator



