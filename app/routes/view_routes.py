from flask import Blueprint, render_template, abort, redirect, url_for, session, g
from app.auth import login_required, role_required, check_page_permission
from utils.logger_config import LOGGER

# Khởi tạo Blueprint
view_bp = Blueprint('view_routes', __name__)



# Trang chủ - Redirect tới dashboard nếu đã đăng nhập, hoặc hiển thị login
@view_bp.route('/')
def index():
    """Trang chủ - kiểm tra đăng nhập và chuyển hướng"""
    # Kiểm tra nếu người dùng đã đăng nhập, chuyển hướng đến dashboard
    if session.get('session_token'):
        return redirect(url_for('view_routes.dashboard'))
    return render_template('login.html')

# Trang đăng nhập (explicit route)
@view_bp.route('/login')
def login():
    """Trang đăng nhập"""
    # Nếu đã đăng nhập, chuyển về dashboard
    if session.get('session_token'):
        return redirect(url_for('view_routes.dashboard'))
    return render_template('login.html')


# Trang Dashboard - Trang chính sau đăng nhập
@view_bp.route('/dashboard')
@login_required
@role_required('dashboard')
def dashboard():
    """Trang dashboard chính"""
    return render_template('dashboard.html', 
                          user_name=g.name,
                          role=g.role,
                          user_id=g.user_id)

# Trang Tracking (Theo dõi chấm công)
@view_bp.route('/tracking')
@login_required
@role_required('tracking')
def tracking():
    """Trang theo dõi chấm công"""
    return render_template('tracking.html',
                          user_name=g.name,
                          role=g.role,
                          user_id=g.user_id)


# Trang phê duyệt
@view_bp.route('/approvals')
@login_required
@role_required('approvals')
def approvals():
    """Trang phê duyệt"""
    return render_template('approvals.html',
                          user_name=g.name,
                          role=g.role,
                          user_id=g.user_id)

# Trang xuất dữ liệu
@view_bp.route('/export')
@login_required
@role_required('export')
def export():
    """Trang xuất dữ liệu"""
    return render_template('export.html',
                          user_name=g.name,
                          role=g.role,
                          user_id=g.user_id)

# Trang feedback
@view_bp.route('/feedbacks')
@login_required
@role_required('feedbacks')
def feedbacks():
    """Trang feedbacks"""
    return render_template('feedbacks.html',
                          user_name=g.name,
                          role=g.role,
                          user_id=g.user_id)

# Trang cài đặt
@view_bp.route('/settings')
@login_required
@role_required('settings')
def settings():
    """Trang cài đặt"""
    return render_template('settings.html',
                          user_name=g.name,
                          role=g.role,
                          user_id=g.user_id)

# Trang users
@view_bp.route('/users')
@login_required
@role_required('users')
def users():
    """Trang users"""
    return render_template('users.html',
                          user_name=g.name,
                          role=g.role,
                          user_id=g.user_id)
