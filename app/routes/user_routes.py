from flask import Blueprint, request, jsonify, send_file, g, current_app, session
import os
import shutil
from config import config
from app import auth, generate_aruco_marker
from app.auth import login_required, role_required, hash_password, check_password
from app.tools import build_faiss_index, generate_username
from utils.insightface_utils import process_image
from insightface_detector import InsightFaceDetector
import unicodedata
import pillow_heif
from PIL import Image
import mimetypes
import re
import time
import random
import cv2

# Khởi tạo Blueprint
user_bp = Blueprint('user_routes', __name__)

# Kết nối MongoDB
user_collection = config.user_collection
feedbacks_collection = config.feedbacks_collection

# Khởi tạo detector
detector = InsightFaceDetector()

# ------------------------------------------------------------
@user_bp.route('/submit_feedback', methods=['POST'])
@login_required
def submit_feedback():
    try:
        # Lấy thông tin user từ session
        session_token = session.get('session_token')
        user = auth.get_user_by_session_token(session_token)
        
        if not user:
            return jsonify({
                "status": "error",
                "message": "Unauthorized"
            }), 401

        # Validate required fields
        required_fields = ["feedback_type", "subject", "priority", "description"]
        for field in required_fields:
            if not request.form.get(field):
                return jsonify({
                    "status": "error",
                    "message": f"Missing required field: {field}"
                }), 400

        # Validate feedback_type
        valid_types = ["bug", "suggestion", "question"]
        if request.form.get("feedback_type") not in valid_types:
            return jsonify({
                "status": "error",
                "message": "Invalid feedback type"
            }), 400

        # Validate priority
        valid_priorities = ["low", "medium", "high", "urgent"]
        if request.form.get("priority") not in valid_priorities:
            return jsonify({
                "status": "error",
                "message": "Invalid priority level"
            }), 400

        # Validate description length
        description = request.form.get("description", "").strip()
        if len(description) < 20:
            return jsonify({
                "status": "error",
                "message": "Description must be at least 20 characters"
            }), 400

        # Validate subject length
        subject = request.form.get("subject", "").strip()
        if len(subject) < 5:
            return jsonify({
                "status": "error",
                "message": "Subject must be at least 5 characters"
            }), 400

        # Prepare feedback data
        feedback_data = {
            "user_id": user.get("user_id"),
            "username": user.get("username"),
            "reporter_name": request.form.get("reporter_name", user.get("name")),
            "reporter_role": request.form.get("reporter_role", user.get("role")),
            "feedback_type": request.form.get("feedback_type"),
            "subject": subject,
            "priority": request.form.get("priority"),
            "description": description,
            "contact_email": request.form.get("contact_email", "").strip(),
            "contact_phone": request.form.get("contact_phone", "").strip(),
            "browser_info": request.form.get("browser_info", ""),
            "screen_resolution": request.form.get("screen_resolution", ""),
            "status": "open",  # open, in_progress, resolved, closed
            "created_at": config.get_vietnam_time(),
            "updated_at": None,
            "resolved_at": None,
            "admin_response": None,
            "attachments": []
        }

        # Handle file uploads
        uploaded_files = request.files.getlist('images')
        if uploaded_files:
            # Create feedbacks folder
            relative_folder_path = user.get("data_folder", "")
            feedbacks_folder = os.path.join(config.BASE_DIR, relative_folder_path, "feedbacks")
            os.makedirs(feedbacks_folder, exist_ok=True)

            # Process each uploaded file
            for file in uploaded_files:
                if file and file.filename:
                    # Validate file type
                    if not file.content_type.startswith('image/'):
                        continue

                    # Validate file size (5MB max)
                    file.seek(0, os.SEEK_END)
                    file_size = file.tell()
                    file.seek(0)
                    
                    if file_size > 5 * 1024 * 1024:  # 5MB
                        continue

                    # Generate unique filename
                    file_extension = os.path.splitext(file.filename)[1].lower()
                    if file_extension not in ['.jpg', '.jpeg', '.png', '.gif']:
                        continue

                    timestamp = int(time.time())
                    safe_filename = f"feedback_{timestamp}_{random.randint(1000, 9999)}{file_extension}"
                    file_path = os.path.join(feedbacks_folder, safe_filename)

                    # Save file
                    file.save(file_path)

                    # Add to attachments list (chỉ tên file)
                    feedback_data["attachments"].append(safe_filename)

        # Insert feedback into database
        result = feedbacks_collection.insert_one(feedback_data)

        if result.inserted_id:
            return jsonify({
                "status": "success",
                "message": "Feedback submitted successfully",
                "data": {
                    "status": "open",
                    "attachments_count": len(feedback_data["attachments"])
                }
            }), 201
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to save feedback"
            }), 500

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to submit feedback: {str(e)}"
        }), 500

# ------------------------------------------------------------
@user_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    data = request.json
    required_fields = ["current_password", "new_password"]
    
    if not all(field in data for field in required_fields):
        return jsonify({
            "status": "error",
            "message": "Missing required fields"
        }), 400

    # Lấy thông tin user từ session
    session_token = session.get('session_token')
    user = auth.get_user_by_session_token(session_token)
    
    if not user:
        return jsonify({
            "status": "error",
            "message": "Unauthorized"
        }), 401
        
    current_username = user.get("username")
    
    # Validate new password length
    new_password = data.get("new_password")
    if len(new_password) < 6:
        return jsonify({
            "status": "error",
            "message": "New password must be at least 6 characters long"
        }), 400
    
    try:
        # Lấy thông tin user từ database
        user_doc = user_collection.find_one({"username": current_username, "active": True})
        
        if not user_doc:
            return jsonify({
                "status": "error",
                "message": "User not found"
            }), 404
            
        # Kiểm tra mật khẩu hiện tại
        current_password = data.get("current_password")
        if not check_password(current_password, user_doc.get("password")):
            return jsonify({
                "status": "error",
                "message": "Current password is incorrect"
            }), 400
            
        # Cập nhật mật khẩu mới
        hashed_new_password = hash_password(new_password)
        
        result = user_collection.update_one(
            {"username": current_username, "active": True},
            {
                "$set": {
                    "password": hashed_new_password,
                    "updated_at": config.get_vietnam_time()
                }
            }
        )
        
        if result.modified_count == 0:
            return jsonify({
                "status": "error",
                "message": "Failed to update password"
            }), 500
            
        return jsonify({
            "status": "success",
            "message": "Password changed successfully"
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to change password: {str(e)}"
        }), 500


# ------------------------------------------------------------
@user_bp.route('/get_users', methods=['GET'])
@login_required
@role_required('get_users')
def get_users():
    try:
        # Lấy tham số từ query
        room_id = request.args.get('room_id', None)
        without_face_embeddings = request.args.get('without_face_embeddings', '1') == '1'

        # Tạo bộ lọc truy vấn MongoDB
        query = {}
        if room_id:
            query['room_id'] = room_id

        users = list(user_collection.find(query))

        for user in users:
            user.pop('_id', None)
            if without_face_embeddings:
                user.pop('face_embeddings', None)
            user.pop('password', None)
            user.pop('sessions', None)
        
        return jsonify({
            "status": "success",
            "data": users,
            "message": "Users retrieved successfully"
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error in get_users: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve users: {str(e)}"
        }), 500


# ------------------------------------------------------------
@user_bp.route('/add_user', methods=['POST'])
@login_required
@role_required('add_user')
def add_user():
    data = request.json
    required_fields = ["name", "room_id", "role"]
    
    if not all(field in data for field in required_fields):
        return jsonify({
            "status": "error",
            "message": "Missing required fields"
        }), 400

    # Lấy thông tin user từ session
    session_token = session.get('session_token')
    user = auth.get_user_by_session_token(session_token)
    
    if not user:
        return jsonify({
            "status": "error",
            "message": "Unauthorized"
        }), 401
        
    current_user_role = user.get("role")
    current_username = user.get("username")
    
    # Kiểm tra quyền hạn tạo user theo role
    requested_role = data.get("role")
    
    # Validate role permissions
    if current_user_role == "admin":
        # Admin chỉ có thể tạo user với role "user" hoặc "admin"
        if requested_role not in ["user", "admin"]:
            return jsonify({
                "status": "error",
                "message": "Admin can only create users with 'user' or 'admin' role"
            }), 403
    elif current_user_role == "super_admin":
        # Super admin có thể tạo user với bất kỳ role nào
        if requested_role not in ["user", "admin", "super_admin"]:
            return jsonify({
                "status": "error",
                "message": "Invalid role specified"
            }), 400
    else:
        # Nếu không phải admin hoặc super_admin thì không có quyền (decorator đã kiểm tra nhưng thêm để đảm bảo)
        return jsonify({
            "status": "error",
            "message": "Insufficient permissions"
        }), 403

    try:
        edulive_users = list(user_collection.find({"user_id": {"$regex": "^EDULIVE\\d+$"}, "active": True}))

        def extract_number(user_doc):
            match = re.search(r"EDULIVE(\d+)", user_doc["user_id"])
            return int(match.group(1)) if match else 0

        edulive_users.sort(key=extract_number, reverse=True)
        new_number = extract_number(edulive_users[0]) + 1 if edulive_users else 1
        user_id = f"EDULIVE{new_number}"

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error generating user ID: {str(e)}"
        }), 500

    folder_path = f"users_data/{user_id}"

    # Gọi hàm generate_username có sẵn
    base_username = generate_username(data["name"])
    username = base_username
    counter = 1
    while user_collection.find_one({"username": username}):
        username = f"{base_username}{counter}"
        counter += 1

    user = {
        "name": data["name"],
        "room_id": data["room_id"],
        "user_id": user_id,
        "username": username,
        "password": hash_password("123456"),
        "telegram_id": data.get("telegram_id"),
        "email": data.get("email"),
        "role": requested_role,
        "created_at": config.get_vietnam_time(),
        "updated_at": None,
        "avatar_file": None,
        "face_embeddings": [],
        "data_folder": folder_path,
        "active": True,
        "created_by": current_username  # Thêm thông tin người tạo
    }

    try:
        user_collection.insert_one(user)
        os.makedirs(folder_path, exist_ok=True)

        # Tạo các thư mục con trong thư mục người dùng
        subfolders = ["attendance_photos", "documents", "feedbacks", "avatar", "face_photos"]
        for sub in subfolders:
            os.makedirs(os.path.join(folder_path, sub), exist_ok=True)

        return jsonify({
            "status": "success",
            "message": "User added successfully",
            "data": {
                "user_id": user_id,
                "username": username,
                "role": requested_role,
                "data_folder": folder_path,
                "created_by": current_username
            }
        }), 201

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to add user: {str(e)}"
        }), 500


# ------------------------------------------------------------
@user_bp.route('/update_user/<user_id>', methods=['PUT'])
@login_required
@role_required('update_user')
def update_user(user_id):
    try:
        # Lấy thông tin user từ session
        session_token = session.get('session_token')
        current_user = auth.get_user_by_session_token(session_token)
        
        if not current_user:
            return jsonify({
                "status": "error",
                "message": "Unauthorized"
            }), 401
            
        current_user_role = current_user.get("role")
        current_user_id = current_user.get("user_id")
        current_username = current_user.get("username")
        
        # Lấy thông tin user cần update
        target_user = user_collection.find_one({"user_id": user_id})
        if not target_user:
            return jsonify({
                "status": "error",
                "message": "User not found"
            }), 404
            
        target_user_role = target_user.get("role")
        
        # Kiểm tra quyền hạn update theo role
        if current_user_role == "user":
            # User chỉ có thể update chính bản thân mình
            if current_user_id != user_id:
                return jsonify({
                    "status": "error",
                    "message": "Users can only update their own profile"
                }), 403
        elif current_user_role == "admin":
            # Admin có thể update admin và user, nhưng không thể update super_admin
            if target_user_role == "super_admin":
                return jsonify({
                    "status": "error",
                    "message": "Admin cannot update super admin accounts"
                }), 403
        elif current_user_role == "super_admin":
            # Super admin có thể update tất cả
            pass
        else:
            # Role không hợp lệ
            return jsonify({
                "status": "error",
                "message": "Invalid user role"
            }), 403

        data = request.get_json()

        # Định nghĩa fields được phép update
        allowed_fields = ['name', 'room_id', 'avatar_file', 'active', 'role', 'telegram_id', 'email']
        
        # Kiểm tra quyền hạn thay đổi role
        if 'role' in data:
            new_role = data['role']
            
            if current_user_role == "user":
                # User không được phép thay đổi role
                return jsonify({
                    "status": "error",
                    "message": "Users cannot change role"
                }), 403
            elif current_user_role == "admin":
                # Admin chỉ có thể set role thành user hoặc admin (không thể tạo super_admin)
                if new_role not in ["user", "admin"]:
                    return jsonify({
                        "status": "error",
                        "message": "Admin can only set role to 'user' or 'admin'"
                    }), 403
                # Admin không thể thay đổi role của super_admin
                if target_user_role == "super_admin":
                    return jsonify({
                        "status": "error",
                        "message": "Admin cannot change super admin's role"
                    }), 403
            elif current_user_role == "super_admin":
                # Super admin có thể set bất kỳ role nào
                if new_role not in ["user", "admin", "super_admin"]:
                    return jsonify({
                        "status": "error",
                        "message": "Invalid role specified"
                    }), 400
        
        # Kiểm tra fields không được phép
        invalid_fields = [k for k in data.keys() if k not in allowed_fields]
        
        if invalid_fields:
            return jsonify({
                "status": "error",
                "message": "Some fields are not allowed to update",
                "data": {"invalid_fields": invalid_fields}
            }), 400

        # Lọc các fields hợp lệ
        update_fields = {k: data[k] for k in allowed_fields if k in data}
        if not update_fields:
            return jsonify({
                "status": "error",
                "message": "No valid fields to update"
            }), 400

        # Thêm thông tin audit
        update_fields['updated_at'] = config.get_vietnam_time()
        update_fields['updated_by'] = current_username

        # Thực hiện update
        result = user_collection.update_one(
            {"user_id": user_id},
            {"$set": update_fields}
        )

        # Log activity
        current_app.logger.info(f"User '{current_username}' ({current_user_role}) updated user {user_id} ({target_user_role}). Fields: {', '.join(update_fields.keys())}")

        return jsonify({
            "status": "success",
            "message": "User updated successfully",
            "data": {
                "updated_fields": {k: v for k, v in update_fields.items() if k not in ['updated_at', 'updated_by']},
                "updated_by": current_username,
                "updated_at": update_fields['updated_at']
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error in update_user: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to update user: {str(e)}"
        }), 500


# ------------------------------------------------------------
@user_bp.route('/delete_user/<user_id>', methods=['DELETE'])
@login_required
@role_required('delete_user')
def delete_user(user_id):
    try:
        user = user_collection.find_one({"user_id": user_id})
        if not user:
            return jsonify({
                "status": "error",
                "message": "User not found"
            }), 404

        relative_folder_path = user.get("data_folder")
        absolute_folder_path = os.path.join(config.BASE_DIR, relative_folder_path)

        def normalize_text(text):
            text = unicodedata.normalize("NFD", text)
            text = text.encode("ascii", "ignore").decode("utf-8")
            return text.replace(" ", "_").lower()

        name_slug = normalize_text(user.get("name", "unknown"))
        time_slug = config.get_vietnam_time().replace(":", "_").replace(" ", "_")
        backup_dir = os.path.join(config.BASE_DIR, "users_data_deleted")
        os.makedirs(backup_dir, exist_ok=True)

        backup_folder = os.path.join(
            backup_dir,
            f"{name_slug}_{user_id}_{time_slug}"
        )

        if absolute_folder_path and os.path.exists(absolute_folder_path):
            shutil.copytree(absolute_folder_path, backup_folder)

        result = user_collection.delete_one({"user_id": user_id})
        if result.deleted_count == 0:
            return jsonify({
                "status": "error",
                "message": "Failed to delete user"
            }), 500

        if absolute_folder_path and os.path.exists(absolute_folder_path):
            shutil.rmtree(absolute_folder_path)

        build_faiss_index()

        return jsonify({
            "status": "success",
            "message": "User deleted and folder backed up successfully",
            "data": {
                "backup_folder": backup_folder
            }
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to delete user: {str(e)}"
        }), 500


# ------------------------------------------------------------
@user_bp.route('/rebuild_all_users_embeddings', methods=['POST'])
@login_required
@role_required('rebuild_all_users_embeddings')
def rebuild_all_users_embeddings():
    try:
        # Chạy xử lý ảnh người dùng
        from app.tools import generate_all_user_embeddings
        generate_all_user_embeddings()
        
        # Cập nhật ann index
        build_faiss_index()
        
        # Log hoạt động
        if hasattr(g, 'username'):
            current_app.logger.info(f"User '{g.username}' rebuilt all user embeddings")
        
        return jsonify({"message": "User photos processed and ann index updated"}), 200
    except Exception as e:
        current_app.logger.error(f"Error in rebuild_all_users_embeddings: {str(e)}")
        return jsonify({"error": f"Failed to process and update: {str(e)}"}), 500


# ------------------------------------------------------------
@user_bp.route('/upload_photo/<user_id>', methods=['POST'])
@login_required
def upload_photo(user_id):
    if 'photo' not in request.files:
        return jsonify({
            "status": "error",
            "message": "No photo uploaded"
        }), 400
    
    upload_type = request.form.get("type")
    if upload_type not in ["face", "avatar"]:
        return jsonify({
            "status": "error",
            "message": "Invalid or missing 'type' (must be 'face' or 'avatar')"
        }), 400
    
    # Lấy thông tin user từ session
    session_token = session.get('session_token')
    current_user = auth.get_user_by_session_token(session_token)
    
    if not current_user:
        return jsonify({
            "status": "error",
            "message": "Unauthorized"
        }), 401
        
    current_user_role = current_user.get("role")
    current_username = current_user.get("username")
    current_user_id = current_user.get("user_id")
    
    # Kiểm tra quyền hạn upload photo theo role
    target_user = user_collection.find_one({"user_id": user_id})
    if not target_user:
        return jsonify({
            "status": "error",
            "message": "User not found"
        }), 404
    
    target_user_role = target_user.get("role")
    
    # Validate upload permissions
    if current_user_role == "user":
        # User chỉ có thể upload photo cho chính mình
        if current_user_id != user_id:
            return jsonify({
                "status": "error",
                "message": "Users can only upload photos for themselves"
            }), 403
    elif current_user_role == "admin":
        # Admin có thể upload photo cho user và admin (không thể upload cho super_admin)
        if target_user_role == "super_admin":
            return jsonify({
                "status": "error",
                "message": "Admin cannot upload photos for super admin users"
            }), 403
    elif current_user_role == "super_admin":
        # Super admin có thể upload photo cho bất kỳ ai
        pass
    else:
        # Nếu không phải user, admin hoặc super_admin thì không có quyền
        return jsonify({
            "status": "error",
            "message": "Insufficient permissions"
        }), 403
    
    photo = request.files['photo']
    original_filename = photo.filename
    is_heic = original_filename.lower().endswith(('.heic', '.heif'))
    filename = os.path.splitext(original_filename)[0] + '.png' if is_heic else original_filename
    
    relative_folder_path = target_user.get("data_folder", "")
    target_folder = os.path.join(config.BASE_DIR, relative_folder_path, "face_photos" if upload_type == "face" else "avatar")
    
    try:
        os.makedirs(target_folder, exist_ok=True)
        file_path = os.path.join(target_folder, filename)
        temp_path = os.path.join(target_folder, "temp_" + original_filename)
        photo.save(temp_path)
        
        if is_heic:
            try:
                pillow_heif.register_heif_opener()
                img = Image.open(temp_path)
                img.save(file_path, format="PNG")
                os.remove(temp_path)
            except Exception as heic_error:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return jsonify({
                    "status": "error",
                    "message": f"Failed to convert HEIC image: {str(heic_error)}"
                }), 400
        else:
            os.rename(temp_path, file_path)
        
        if upload_type == "face":
            existing_photos = {entry["photo_name"] for entry in target_user.get("face_embeddings", []) or []}
            if filename in existing_photos:
                os.remove(file_path)
                return jsonify({
                    "status": "error",
                    "message": "Photo already exists"
                }), 400
            
            face_embedding, processing_message = process_image(file_path, detector)
            if face_embedding is None:
                os.remove(file_path)
                return jsonify({
                    "status": "error",
                    "message": processing_message
                }), 400
            
            embedding_entry = {
                "photo_name": filename,
                "embedding": face_embedding.tolist(),
                "uploaded_by": current_username,
                "uploaded_at": config.get_vietnam_time()
            }
            
            user_collection.update_one(
                {"user_id": user_id},
                {
                    "$push": {"face_embeddings": embedding_entry},
                    "$set": {"updated_at": config.get_vietnam_time()}
                }
            )
            build_faiss_index()
            
            return jsonify({
                "status": "success",
                "message": "Face photo uploaded and features saved",
                "data": {
                    "photo_name": filename,
                    "processing_details": processing_message + (" (Converted from HEIC to PNG)" if is_heic else ""),
                    "converted": is_heic,
                    "uploaded_by": current_username
                }
            }), 200
        else:
            user_collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "avatar_file": filename,
                        "updated_at": config.get_vietnam_time()
                    }
                }
            )
            
            return jsonify({
                "status": "success",
                "message": "Avatar uploaded successfully",
                "data": {
                    "photo_name": filename,
                    "converted": is_heic,
                    "uploaded_by": current_username
                }
            }), 200
            
    except Exception as e:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({
            "status": "error",
            "message": f"Failed to upload photo: {str(e)}"
        }), 500


# ------------------------------------------------------------
@user_bp.route('/delete_photo/<user_id>', methods=['DELETE'])
# @login_required
# @role_required('delete_photo')
def delete_photo(user_id):
    try:
        data = request.get_json()

        if not data or "file_name" not in data or "type" not in data:
            return jsonify({
                "status": "error",
                "message": "Both 'file_name' and 'type' are required"
            }), 400

        file_name = data["file_name"]
        delete_type = data["type"]

        if delete_type not in ["face", "avatar"]:
            return jsonify({
                "status": "error",
                "message": "Invalid 'type'. Must be 'face' or 'avatar'"
            }), 400

        user = user_collection.find_one({"user_id": user_id})
        if not user:
            return jsonify({
                "status": "error",
                "message": "User not found"
            }), 404

        relative_folder_path = user.get("data_folder", "")
        subfolder = "face_photos" if delete_type == "face" else "avatar"
        photo_path = os.path.join(config.BASE_DIR, relative_folder_path, subfolder)

        if not photo_path:
            return jsonify({
                "status": "error",
                "message": "User folder not found"
            }), 500

        full_path = os.path.join(photo_path, file_name)

        if not os.path.exists(full_path):
            return jsonify({
                "status": "error",
                "message": "File not found"
            }), 404

        os.remove(full_path)

        if delete_type == "face":
            user_collection.update_one(
                {"user_id": user_id},
                {"$pull": {"face_embeddings": {"photo_name": file_name}}}
            )
            build_faiss_index()
        else:  # delete_type == "avatar"
            user_collection.update_one(
                {"user_id": user_id},
                {"$set": {"avatar_file": None}}
            )

        return jsonify({
            "status": "success",
            "message": f"{delete_type.capitalize()} photo deleted successfully",
            "data": {"photo_name": file_name}
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to delete photo: {str(e)}"
        }), 500


# ------------------------------------------------------------
@user_bp.route('/get_photos/<user_id>', methods=['GET'])
@login_required
@role_required('get_photos')
def get_photos(user_id):
    try:
        photo_type = request.args.get("type")
        if photo_type not in ["face", "avatar"]:
            return jsonify({
                "status": "error",
                "message": "Invalid or missing 'type'. Must be 'face' or 'avatar'"
            }), 400

        user = user_collection.find_one({"user_id": user_id})
        if not user:
            return jsonify({
                "status": "error",
                "message": "User not found"
            }), 404

        relative_folder_path = user.get("data_folder", "")
        subfolder = "face_photos" if photo_type == "face" else "avatar"
        photo_folder = os.path.join(config.BASE_DIR, relative_folder_path, subfolder)

        if not photo_folder:
            return jsonify({
                "status": "error",
                "message": "User folder not found"
            }), 500

        if not os.path.exists(photo_folder):
            return jsonify({
                "status": "error",
                "message": f"{photo_type.capitalize()} photo folder does not exist"
            }), 404

        photos = [
            f for f in os.listdir(photo_folder)
            if os.path.isfile(os.path.join(photo_folder, f))
        ]

        return jsonify({
            "status": "success",
            "message": f"{photo_type.capitalize()} photos retrieved successfully",
            "data": {
                "type": photo_type,
                "photos": photos
            }
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve photos: {str(e)}"
        }), 500


# ------------------------------------------------------------
@user_bp.route('/view_face_photo/<user_id>/<filename>', methods=['GET'])
@login_required
@role_required('view_face_photo')
def view_face_photo(user_id, filename):
    try:
        user = user_collection.find_one({"user_id": user_id})
        if not user:
            return jsonify({
                "status": "error",
                "message": "User not found"
            }), 404

        relative_folder_path = user.get("data_folder", "")
        face_photos_path = os.path.join(config.BASE_DIR, relative_folder_path, "face_photos")
        if not face_photos_path:
            return jsonify({
                "status": "error",
                "message": "User folder not found"
            }), 500

        file_path = os.path.join(face_photos_path, filename)

        if not os.path.exists(file_path):
            return jsonify({
                "status": "error",
                "message": "Photo not found"
            }), 404

        mimetype = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
        return send_file(file_path, mimetype=mimetype)

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to load photo: {str(e)}"
        }), 500


# ------------------------------------------------------------
@user_bp.route('/view_avatar/<user_id>', methods=['GET'])
@login_required
@role_required('view_avatar')
def view_avatar(user_id):
    try:
        user = user_collection.find_one({"user_id": user_id})
        if not user:
            return jsonify({
                "status": "error",
                "message": "User not found"
            }), 404

        avatar_file = user.get("avatar_file")
        if not avatar_file:
            return jsonify({
                "status": "error",
                "message": "No avatar selected"
            }), 404

        relative_folder_path = user.get("data_folder", "")
        avatar_path = os.path.join(config.BASE_DIR, relative_folder_path, "avatar", avatar_file)
        
        if not os.path.exists(avatar_path):
            return jsonify({
                "status": "error",
                "message": "Avatar file not found"
            }), 404

        mimetype = mimetypes.guess_type(avatar_path)[0] or 'application/octet-stream'
        return send_file(avatar_path, mimetype=mimetype)

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to load avatar: {str(e)}"
        }), 500


# ------------------------------------------------------------
@user_bp.route('/get_user/<user_id>', methods=['GET'])
def get_user(user_id):
    try:
        user = user_collection.find_one({"user_id": user_id}, {
            "_id": 0,
            "password": 0,
            "face_embeddings": 0,
            "data_folder": 0,
            "updated_at": 0,
            "updated_by": 0,
            "created_by": 0,
            "sessions": 0,
            "active": 0,
            "avatar_file": 0,
            "username": 0,
            "user_id": 0
        })

        if not user:
            return jsonify({
                "status": "error",
                "message": "User not found"
            }), 404

        # Loại bỏ các trường không cần thiết (nếu có)
        user.pop("_id", None)
        user.pop("password", None)
        user.pop("face_embeddings", None)

        return jsonify({
            "status": "success",
            "data": user
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to fetch user: {str(e)}"
        }), 500


@user_bp.route("/get_qr_code", methods=["GET"])
def get_qr_code():
    try:
        marker_id = int(request.args.get("id", 0))
        size = int(request.args.get("size", 400))
        dictionary_name = request.args.get("marker", "DICT_5X5_100")

        marker_image = generate_aruco_marker(dictionary_name, marker_id, size)

        # Encode ảnh thành PNG và đưa vào bộ nhớ RAM
        success, encoded_image = cv2.imencode(".png", marker_image)
        if not success:
            raise RuntimeError("Failed to encode marker image.")
        
        # Dùng BytesIO giả lập file
        image_io = io.BytesIO(encoded_image.tobytes())
        image_io.seek(0)

        return send_file(image_io, mimetype="image/png", as_attachment=False)

    except Exception as e:
        return jsonify({"error": str(e)}), 400







# user_collection = config.user_collection

# def preview_username_updates():
#     """
#     Preview tất cả các thay đổi username sẽ được thực hiện
#     """
#     print("=" * 80)
#     print("PREVIEW: Username Updates")
#     print("=" * 80)
    
#     # Lấy tất cả users
#     users = list(user_collection.find({}, {"_id": 1, "name": 1, "username": 1}))
    
#     if not users:
#         print("❌ Không tìm thấy user nào trong collection!")
#         return
    
#     print(f"📊 Tổng số users: {len(users)}")
#     print()
    
#     # Tạo danh sách username mới và check duplicates
#     username_map = {}  # {user_id: new_username}
#     username_counts = {}  # {base_username: count}
    
#     # Preview từng user
#     print("📋 Chi tiết thay đổi:")
#     print("-" * 80)
#     print(f"{'STT':<4} {'Tên hiện tại':<25} {'Username cũ':<15} {'Username mới':<15}")
#     print("-" * 80)
    
#     for idx, user in enumerate(users, 1):
#         user_id = user["_id"]
#         current_name = user.get("name", "")
#         current_username = user.get("username", "")
        
#         # Tạo base username
#         base_username = generate_username(current_name)
        
#         # Xử lý duplicate
#         if base_username in username_counts:
#             username_counts[base_username] += 1
#             new_username = f"{base_username}{username_counts[base_username]}"
#         else:
#             username_counts[base_username] = 0
#             new_username = base_username
        
#         username_map[user_id] = new_username
        
#         # Hiển thị thông tin
#         status = "🔄" if current_username != new_username else "✅"
#         print(f"{idx:<4} {current_name:<25} {current_username:<15} {new_username:<15} {status}")
    
#     print("-" * 80)
    
#     # Thống kê
#     total_users = len(users)
#     users_with_changes = sum(1 for user in users if user.get("username", "") != username_map[user["_id"]])
#     users_without_changes = total_users - users_with_changes
    
#     print(f"\n📈 Thống kê:")
#     print(f"   • Tổng số users: {total_users}")
#     print(f"   • Users sẽ được update username: {users_with_changes}")
#     print(f"   • Users không thay đổi: {users_without_changes}")
#     print(f"   • Password sẽ được reset về '123456' cho TẤT CẢ users")
    
#     # Kiểm tra duplicate usernames
#     duplicates = {k: v for k, v in username_counts.items() if v > 0}
#     if duplicates:
#         print(f"\n⚠️  Username trùng lặp (sẽ được đánh số):")
#         for base, count in duplicates.items():
#             print(f"   • {base}: {count + 1} users ({base}, {base}1, {base}2, ...)")
    
#     return username_map

# def preview_password_updates():
#     """
#     Preview password updates
#     """
#     print("\n" + "=" * 80)
#     print("PREVIEW: Password Updates")
#     print("=" * 80)
    
#     total_users = user_collection.count_documents({})
#     print(f"🔑 TẤT CẢ {total_users} users sẽ có password được reset về: '123456'")
#     print("   (Password sẽ được hash bằng hàm hash_password)")
    
# def main():
#     """
#     Chạy preview toàn bộ
#     """
#     try:
#         # Preview username changes
#         username_map = preview_username_updates()
        
#         # Preview password changes  
#         preview_password_updates()
        
#         print("\n" + "=" * 80)
#         print("⚠️  LƯU Ý: Đây chỉ là PREVIEW - Chưa có thay đổi nào được thực hiện!")
#         print("   Để thực hiện update thực sự, hãy chạy hàm execute_updates()")
#         print("=" * 80)
        
#         return username_map
        
#     except Exception as e:
#         print(f"❌ Lỗi khi preview: {e}")
#         return None

# def execute_updates(username_map=None):
#     """
#     Thực hiện update thực sự (chỉ chạy sau khi đã preview và xác nhận)
#     """
#     if username_map is None:
#         print("❌ Vui lòng chạy preview trước!")
#         return
    
#     confirm = input("\n🚨 BẠN CÓ CHẮC MUỐN THỰC HIỆN UPDATE? (yes/no): ").lower()
#     if confirm != 'yes':
#         print("❌ Đã hủy update!")
#         return
    
#     print("\n🔄 Đang thực hiện update...")
    
#     try:
#         success_count = 0
#         error_count = 0
        
#         for user_id, new_username in username_map.items():
#             try:
#                 # Update username và password
#                 result = user_collection.update_one(
#                     {"_id": user_id},
#                     {
#                         "$set": {
#                             "username": new_username,
#                             "password": hash_password("123456")  # Bạn cần import hàm này
#                         }
#                     }
#                 )
                
#                 if result.modified_count > 0:
#                     success_count += 1
#                 else:
#                     print(f"⚠️  User {user_id} không được update (có thể đã giống rồi)")
                    
#             except Exception as e:
#                 print(f"❌ Lỗi update user {user_id}: {e}")
#                 error_count += 1
        
#         print(f"\n✅ Hoàn thành!")
#         print(f"   • Thành công: {success_count} users")
#         print(f"   • Lỗi: {error_count} users")
        
#     except Exception as e:
#         print(f"❌ Lỗi nghiêm trọng: {e}")


# username_map = main()
    
#     # Uncomment dòng dưới để thực hiện update thực sự sau khi preview
# execute_updates(username_map)