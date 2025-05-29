from flask import Flask
from flask_cors import CORS
from datetime import timedelta
import os
from dotenv import load_dotenv
from utils.logger_config import LOGGER  # Sử dụng LOGGER có sẵn
from qr_code.generate_aruco_tags import generate_aruco_marker

# Tải biến môi trường nếu có
try:
    load_dotenv()
except ImportError:
    pass

# Xác định môi trường
ENV = os.getenv('FLASK_ENV', 'development')
DEBUG = ENV == 'development'

# Khởi tạo ứng dụng Flask
app = Flask(__name__)

# Cấu hình môi trường
app.config['ENV'] = ENV
app.config['DEBUG'] = DEBUG

# Cấu hình CORS với credentials
CORS(app, supports_credentials=True)

# Cấu hình cho session
app.secret_key = os.getenv("FLASK_SECRET_KEY", "YNK4FsxP7QdZ8tHu3BvT5jLrW9eG2mCa")  # Sử dụng biến môi trường nếu có
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Cookie HttpOnly
app.config['SESSION_COOKIE_SECURE'] = ENV == 'production'  # Yêu cầu HTTPS trong production
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Phòng chống CSRF
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)  # Thời gian sống của session

# Token nội bộ cho API gọi nội bộ
app.config['INTERNAL_TOKEN'] = os.getenv("INTERNAL_TOKEN", "")
if not app.config['INTERNAL_TOKEN'] and ENV == 'production':
    LOGGER.warning("INTERNAL_TOKEN not set in production environment")

# Kết nối MongoDB từ config
from config import config
reports_collection = config.reports_collection
user_collection = config.user_collection

# Đảm bảo có index cho session token trong MongoDB
user_collection.create_index('sessions.token')
user_collection.create_index('user_id', unique=True)
user_collection.create_index(
    [('username', 1)], 
    unique=True, 
    partialFilterExpression={'username': {'$type': 'string'}}
)

# Import các module khác
from app.routes import auth_routes, user_routes, camera_routes, attendance_routes, view_routes
from app.tools import build_faiss_index

# Đăng ký các blueprint
app.register_blueprint(auth_routes.auth_bp, url_prefix='/api')
app.register_blueprint(user_routes.user_bp, url_prefix='/api')
app.register_blueprint(camera_routes.camera_bp, url_prefix='/api')
app.register_blueprint(attendance_routes.attendance_bp, url_prefix='/api')
app.register_blueprint(view_routes.view_bp)

# Thêm hàm check_page_permission vào các template Jinja2
from app.auth import check_page_permission

@app.context_processor
def utility_processor():
    return dict(check_page_permission=check_page_permission)