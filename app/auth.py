from functools import wraps, lru_cache
from flask import request, jsonify, session, redirect, url_for, g, current_app
from datetime import datetime, timedelta, timezone
import uuid
import bcrypt
import os
import hashlib
from utils.logger_config import LOGGER
from config import config

# Lấy collection từ config
user_collection = config.user_collection

# Define role hierarchy and permissions
ROLES_HIERARCHY = {
    'super_admin': ['admin', 'user'],  # Super admin can do everything
    'admin': ['user'],                 # Admin can do admin and user actions
    'user': []                         # User can only do user actions
}

# Define permissions for each API endpoint
API_PERMISSIONS = {
    # User management
    'get_users': ['user', 'admin', 'super_admin'],
    'add_user': ['admin', 'super_admin'],
    'get_user': ['admin', 'super_admin'],
    'delete_user': ['admin', 'super_admin'],
    'upload_photo': ['admin', 'super_admin'],
    'upload_face_photo': ['admin', 'super_admin'],
    'upload_avatar': ['admin', 'super_admin'],
    'delete_face_photo': ['admin', 'super_admin'],
    'get_photos': ['admin', 'super_admin'],
    'view_photo': ['admin', 'super_admin'],
    'view_avatar': ['user', 'admin', 'super_admin'],
    'get_user_data': ['admin', 'super_admin'],
    'view_face_photo': ['admin', 'super_admin'],
    
    # Attendance data
    'get_attendance': ['user', 'admin', 'super_admin'],
    'get_attendances': ['user', 'admin', 'super_admin'],
    'export_attendance': ['admin', 'super_admin'],
    'generate_excel': ['admin', 'super_admin'],
    'download': ['admin', 'super_admin'],
    'rebuild_all_users_embeddings': ['super_admin'],
    'get_qr_code': ['admin', 'super_admin'],
    'view_attendance_photo': ['user', 'admin', 'super_admin'],

    # Camera
    'get_cameras': ['admin', 'super_admin'],
    'get_camera': ['admin', 'super_admin'],
    'add_camera': ['admin', 'super_admin'],
    'delete_camera': ['admin', 'super_admin'],
    'update_camera': ['admin', 'super_admin'],
    
    # Trang web
    'dashboard': ['user', 'admin', 'super_admin'],
    'tracking': ['user', 'admin', 'super_admin'],
    'users': ['admin', 'super_admin'],
    'feedbacks': ['user', 'admin', 'super_admin'],
    'settings': ['user', 'admin', 'super_admin'],
    'export': ['admin', 'super_admin'],
    'approvals': ['admin', 'super_admin'],
}

# Check if user has permission based on role
def has_permission(user_role, required_role):
    if user_role == required_role:
        return True
    
    # Check if user's role inherits the required role
    if required_role in ROLES_HIERARCHY.get(user_role, []):
        return True
    
    return False

# Helper function to hash password
def hash_password(password):
    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')

# Helper function to check password
def check_password(password, hashed_password):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

# Function to validate internal token
def validate_internal_token(request):
    """
    Kiểm tra Internal-Token trong header request
    
    Tham số:
    - request: Flask request object
    
    Trả về:
    - bool: True nếu token hợp lệ, False nếu không
    """
    token = request.headers.get('Authorization')
    if token and token.startswith('Bearer '):
        token = token.split(' ')[1]
    else:
        token = request.headers.get('Internal-Token')
    
    internal_token = current_app.config.get('INTERNAL_TOKEN')
    
    # Nếu token hợp lệ và không rỗng
    return internal_token and token == internal_token

# Hàm tạo mã thông báo phiên an toàn
def create_secure_session_token():
    """Tạo session token an toàn hơn kết hợp UUID và random bytes"""
    random_bytes = os.urandom(16)  # 16 bytes của dữ liệu ngẫu nhiên
    unique_id = str(uuid.uuid4())  # UUID v4
    combined = random_bytes + unique_id.encode('utf-8')
    return hashlib.sha256(combined).hexdigest()

# Session management functions
def create_session(user_id, remember=False):
    """
    Tạo session mới và lưu trong user_collection
    
    Tham số:
    - user_id: ID của người dùng
    - remember: True nếu muốn lưu session lâu dài
    
    Trả về:
    - session_token: Token phiên dùng được lưu trong cookie
    - expires_at: Thời gian hết hạn của phiên
    """
    session_token = create_secure_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=30 if remember else 1)
    
    # Thông tin thiết bị và vị trí
    user_agent = request.user_agent.string if request.user_agent else "Unknown"
    ip_address = request.remote_addr or "Unknown"
    
    # Tạo document session
    session_data = {
        'token': session_token,
        'created_at': datetime.now(timezone.utc),
        'expires_at': expires_at,
        'device': user_agent,
        'ip': ip_address,
        'last_activity': datetime.now(timezone.utc)
    }
    
    # Thêm session mới vào user
    user_collection.update_one(
        {'user_id': user_id},
        {'$push': {'sessions': session_data}}
    )
    
    # Xóa các session hết hạn
    user_collection.update_one(
        {'user_id': user_id},
        {'$pull': {'sessions': {'expires_at': {'$lt': datetime.now(timezone.utc)}}}}
    )
    
    return session_token, expires_at

def get_user_by_session_token(token):
    """
    Tìm người dùng bằng session token
    
    Tham số:
    - token: Session token
    
    Trả về:
    - user: Document người dùng nếu tìm thấy, None nếu không tìm thấy
    """
    return user_collection.find_one({
        'sessions.token': token,
        'sessions.expires_at': {'$gt': datetime.now(timezone.utc)}
    })

def update_session_activity(user_id, token):
    """
    Cập nhật thời gian hoạt động cuối của session
    
    Tham số:
    - user_id: ID của người dùng
    - token: Session token
    """
    user_collection.update_one(
        {
            'user_id': user_id,
            'sessions.token': token
        },
        {'$set': {
            'sessions.$.last_activity': datetime.now(timezone.utc)
        }}
    )

def remove_session(token):
    """
    Xóa session
    
    Tham số:
    - token: Session token
    """
    user_collection.update_one(
        {'sessions.token': token},
        {'$pull': {'sessions': {'token': token}}}
    )

def remove_all_sessions(user_id):
    """
    Xóa tất cả session của người dùng
    
    Tham số:
    - user_id: ID của người dùng
    """
    user_collection.update_one(
        {'user_id': user_id},
        {'$set': {'sessions': []}}
    )

# Helper function for creating consistent error responses
def create_error_response(message, error_code=None, status_code=400):
    """Tạo phản hồi lỗi với định dạng nhất quán"""
    response = {
        'success': False,
        'message': message
    }
    if error_code:
        response['error'] = error_code
    return jsonify(response), status_code

# Unified authentication handler
def authenticate_user():
    """
    Xác thực người dùng từ session hoặc internal token
    
    Trả về:
    - (bool, response): Tuple gồm:
        - bool: True nếu xác thực thành công, False nếu thất bại
        - response: None nếu xác thực thành công, response object nếu thất bại
    """
    # Kiểm tra internal token trước
    if validate_internal_token(request):
        # Đặt g.is_internal_call để đánh dấu đây là internal call
        g.is_internal_call = True
        LOGGER.debug("Authentication via internal token")
        return True, None
    
    # Nếu không có internal token, kiểm tra session
    session_token = session.get('session_token')
    if not session_token:
        # Nếu là API, trả về lỗi JSON
        LOGGER.warning(f"Authentication failed: No session token. Path: {request.path}")
        if request.path.startswith('/api/'):
            return False, create_error_response("Authentication required", "auth_required", 401)
        else:
            # Chuyển hướng về trang login
            return False, redirect(url_for('view_routes.index'))
    
    # Tìm user dựa trên session token
    user = get_user_by_session_token(session_token)
    if not user:
        # Session không tồn tại hoặc đã hết hạn
        session.clear()
        LOGGER.warning(f"Authentication failed: Invalid or expired session token")
        
        # Nếu là API, trả về lỗi JSON
        if request.path.startswith('/api/'):
            return False, create_error_response("Session expired or invalid", "session_expired", 401)
        else:
            # Chuyển hướng về trang login
            return False, redirect(url_for('view_routes.index'))
    
    # Lưu thông tin user vào g để sử dụng trong route
    g.user_id = user['user_id']
    g.username = user['username']
    g.role = user.get('role', 'user')
    g.name = user.get('name', '')
    g.is_internal_call = False
    
    # Cập nhật thời gian hoạt động
    update_session_activity(g.user_id, session_token)
    
    LOGGER.debug(f"User '{g.username}' authenticated successfully via session")
    return True, None

# Hàm decorator để bảo vệ các route yêu cầu đăng nhập
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Xác thực người dùng
        auth_success, auth_response = authenticate_user()
        if not auth_success:
            return auth_response
        
        return f(*args, **kwargs)
    return decorated_function

# Cache roles to improve performance
@lru_cache(maxsize=128)
def get_required_roles(endpoint_name):
    """Lấy danh sách các vai trò cần thiết cho endpoint, có cache"""
    return API_PERMISSIONS.get(endpoint_name, [])

# Role-based access decorator
def role_required(endpoint_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Xác thực người dùng
            auth_success, auth_response = authenticate_user()
            if not auth_success:
                return auth_response
            
            # Nếu là internal call, bypass kiểm tra quyền
            if getattr(g, 'is_internal_call', False):
                LOGGER.debug(f"Permission check bypassed via internal token for endpoint: {endpoint_name}")
                return f(*args, **kwargs)
            
            # Kiểm tra quyền
            user_role = g.role
            required_roles = get_required_roles(endpoint_name)

            if not required_roles:
                LOGGER.warning(f"No permissions defined for endpoint: {endpoint_name}")
                return create_error_response("No permissions defined for this endpoint", None, 403)
            
            has_access = any(has_permission(user_role, role) for role in required_roles)
            if not has_access:
                LOGGER.warning(f"Access denied: User '{g.username}' with role '{user_role}' attempted to access '{endpoint_name}'")
                return create_error_response("Access denied: Insufficient permissions", None, 403)

            LOGGER.debug(f"User '{g.username}' with role '{user_role}' granted access to '{endpoint_name}'")
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Helper function to apply RBAC to page routes as well
def check_page_permission(endpoint_name):
    # Kiểm tra nếu là internal token
    if validate_internal_token(request):
        return True
    
    # Kiểm tra session token
    session_token = session.get('session_token')
    if not session_token:
        return False
    
    # Tìm user
    user = get_user_by_session_token(session_token)
    if not user:
        # Session không tồn tại hoặc đã hết hạn
        session.clear()
        return False
    
    # Lấy role và kiểm tra quyền
    user_role = user.get('role', 'user')
    required_roles = get_required_roles(endpoint_name)

    
    if not required_roles:
        return False
    
    # Kiểm tra quyền
    return any(has_permission(user_role, role) for role in required_roles)