from flask import Blueprint, request, jsonify, render_template, session, current_app, g
from utils.logger_config import LOGGER
from app.auth import (
    check_password, 
    login_required, 
    create_session, 
    remove_session, 
    has_permission, 
    API_PERMISSIONS,
    get_user_by_session_token,
    update_session_activity
)
from datetime import timedelta
from config import config

# Lấy collection từ config
user_collection = config.user_collection

# Khởi tạo Blueprint
auth_bp = Blueprint('auth_routes', __name__)


# ------------------------------------------------------------------------------------------------
@auth_bp.route('/auth/login', methods=['POST'])
def api_login():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        remember = data.get('remember', False)

        if not username or not password:
            return jsonify({
                "status": "error",
                "message": "Username and password are required"
            }), 400

        user = user_collection.find_one({'username': username})
        if not user or not check_password(password, user.get('password', '')):
            return jsonify({
                "status": "error",
                "message": "Invalid username or password"
            }), 401

        session_token, expires_at = create_session(
            user_id=user['user_id'],
            remember=remember
        )

        role = user.get('role', 'user')

        session.clear()
        session['session_token'] = session_token
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        session['role'] = role

        if remember:
            session.permanent = True
            # Flask config should define permanent_session_lifetime if needed

        user_info = {
            'user_id': user['user_id'],
            'username': user['username'],
            'name': user.get('name', ''),
            'role': role,
            'avatar_file': user.get('avatar_file', ''),
            'created_at': user.get('created_at', ''),
            'updated_at': user.get('updated_at', ''),
            'permissions': {}
        }

        for endpoint, required_roles in API_PERMISSIONS.items():
            has_access = any(has_permission(role, req_role) for req_role in required_roles)
            user_info['permissions'][endpoint] = has_access

        return jsonify({
            "status": "success",
            "message": "Authentication successful",
            "data": {
                "user": user_info,
                "session_expires": expires_at.isoformat() if remember else None
            }
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Authentication failed: {str(e)}"
        }), 500


# ------------------------------------------------------------------------------------------------
# User logout API
@auth_bp.route('/auth/logout', methods=['POST'])
@login_required
def api_logout():
    try:
        user_id = session.get('user_id')
        token = session.get('session_token')

        # Xoá session khỏi server (MongoDB hoặc nơi bạn lưu)
        if token:
            remove_session(token)  # Hàm bạn định nghĩa

        session.clear()

        return jsonify({
            "status": "success",
            "message": "Logout successful"
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Logout failed: {str(e)}"
        }), 500
