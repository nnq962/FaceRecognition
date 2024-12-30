from flask import Flask, request, jsonify, Response
from pymongo import MongoClient
from datetime import datetime
import os
import io
import csv
import shutil
from insightface_detector import InsightFaceDetector
from build_database import update_embeddings_for_all_users, create_faiss_index_with_mongo_id_cosine

app = Flask(__name__)
detector = InsightFaceDetector()

# Kết nối tới MongoDB
client = MongoClient("mongodb://localhost:27017/") 
db = client["my_database"] 
users_collection = db["camera_users"]
managers_collection = db["camera_managers"]
camera_collection = db["camera_information"]
data_collection = db["camera_data"]

# ----------------------------------------------------------------
@app.route('/add_user', methods=['POST'])
def add_user():
    data = request.json

    # Kiểm tra dữ liệu đầu vào
    required_fields = ["full_name", "username", "password", "department_id"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    # Tạo ID tự động tăng dần
    last_user = users_collection.find_one(sort=[("_id", -1)])  # Lấy user có _id lớn nhất
    user_id = last_user["_id"] + 1 if last_user else 1  # Tăng ID nếu có, bắt đầu từ 1 nếu chưa có user nào

    # Chuẩn bị dữ liệu để thêm vào MongoDB
    user = {
        "_id": user_id,
        "full_name": data["full_name"],
        "username": data["username"],
        "password": data["password"],  # Lưu trực tiếp mật khẩu
        "department_id": data["department_id"],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # Thêm user vào collection
    users_collection.insert_one(user)
    return jsonify({"message": "User added", "id": user_id})

# ----------------------------------------------------------------
# API: Lấy danh sách users
@app.route('/get_users', methods=['GET'])
def get_users():
    users = list(users_collection.find())
    return jsonify(users)

# ----------------------------------------------------------------
@app.route('/delete_image', methods=['DELETE'])
def delete_image():
    data = request.json

    # Kiểm tra đầu vào
    required_fields = ["username", "password", "image_path"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    username = data["username"]
    password = data["password"]
    image_name = data["image_path"]  # Tên ảnh

    # Kiểm tra user có tồn tại và mật khẩu đúng không
    user = users_collection.find_one({"username": username, "password": password})
    if not user:
        return jsonify({"error": "Invalid username or password"}), 401

    user_id = user["_id"]
    user_dir = f"data_set/{user_id}"
    image_path = os.path.join(user_dir, image_name)  # Tạo đường dẫn đầy đủ

    # Kiểm tra xem ảnh có tồn tại trong MongoDB không
    image_record = users_collection.find_one({"_id": user_id, "images.path": image_path})
    if not image_record:
        return jsonify({"error": "Image not found in the database"}), 404

    # Xóa thông tin ảnh trong MongoDB
    users_collection.update_one(
        {"_id": user_id},
        {"$pull": {"images": {"path": image_path}}}
    )

    # Xóa ảnh vật lý trong thư mục
    try:
        if os.path.exists(image_path):
            os.remove(image_path)
            # Gọi các hàm chỉ khi việc xoá ảnh thành công
            try:
                update_embeddings_for_all_users(detector=detector)
                create_faiss_index_with_mongo_id_cosine()
            except Exception as e:
                return jsonify({"error": f"Failed to update embeddings or FAISS index: {str(e)}"}), 500
            return jsonify({"message": "Image deleted successfully"}), 200
        else:
            return jsonify({"error": "Image file not found in the directory"}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to delete image: {str(e)}"}), 500
# ----------------------------------------------------------------

# Tạo API thêm ảnh cho user
@app.route('/add_image', methods=['POST'])
def add_image():
    data = request.json

    # Kiểm tra đầu vào
    required_fields = ["username", "password", "image_path"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    username = data["username"]
    password = data["password"]
    image_path = data["image_path"]

    # Kiểm tra user có tồn tại và mật khẩu đúng không
    user = users_collection.find_one({"username": username, "password": password})
    if not user:
        return jsonify({"error": "Invalid username or password"}), 401

    # Lấy _id của user và tạo thư mục nếu chưa tồn tại
    user_id = user["_id"]
    user_dir = f"data_set/{user_id}"
    os.makedirs(user_dir, exist_ok=True)

    # Sao chép ảnh vào thư mục user
    try:
        if os.path.exists(image_path):  # Kiểm tra đường dẫn ảnh có tồn tại
            file_name = os.path.basename(image_path)
            new_path = os.path.join(user_dir, file_name)

            # Kiểm tra xem ảnh đã tồn tại trong thư mục đích chưa
            if os.path.exists(new_path):
                return jsonify({"error": "Image already exists in the destination"}), 409

            # Sao chép ảnh
            shutil.copy(image_path, new_path)

            # Cập nhật đường dẫn ảnh trong MongoDB
            users_collection.update_one(
                {"_id": user_id},
                {"$push": {"images": {"path": new_path}}}            
            )

            # Gọi các hàm chỉ khi việc thêm ảnh thành công
            try:
                update_embeddings_for_all_users(detector=detector)
                create_faiss_index_with_mongo_id_cosine()
            except Exception as e:
                return jsonify({"error": f"Failed to update embeddings or FAISS index: {str(e)}"}), 500

            return jsonify({"message": "Image added successfully", "image_path": new_path}), 200
        else:
            return jsonify({"error": "Image file not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to add image: {str(e)}"}), 50
# ----------------------------------------------------------------
@app.route('/delete_user', methods=['DELETE'])
def delete_user():
    data = request.json

    # Kiểm tra đầu vào
    required_fields = ["username", "password"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    username = data["username"]
    password = data["password"]

    # Kiểm tra user có tồn tại và mật khẩu đúng không
    user = users_collection.find_one({"username": username, "password": password})
    if not user:
        return jsonify({"error": "Invalid username or password"}), 401

    # Xóa user khỏi MongoDB
    user_id = user["_id"]
    result = users_collection.delete_one({"_id": user_id})

    # Xóa thư mục chứa ảnh của user
    user_dir = f"data_set/{user_id}"
    if os.path.exists(user_dir):
        try:
            import shutil
            shutil.rmtree(user_dir)  # Xóa toàn bộ thư mục
        except Exception as e:
            return jsonify({"error": f"Failed to delete user folder: {str(e)}"}), 500

    if result.deleted_count > 0:

        # Gọi các hàm chỉ khi việc xoá user thành công
        try:
            update_embeddings_for_all_users(detector=detector)
            create_faiss_index_with_mongo_id_cosine()
        except Exception as e:
            return jsonify({"error": f"Failed to update embeddings or FAISS index: {str(e)}"}), 500
        
        return jsonify({"message": "User deleted successfully"}), 200
    else:
        return jsonify({"error": "Failed to delete user"}), 500

# ----------------------------------------------------------------
@app.route('/add_camera_manager', methods=['POST'])
def add_camera_manager():
    data = request.json

    # Kiểm tra dữ liệu đầu vào
    required_fields = ["camera_id", "fullname", "department_id", "username", "password"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    camera_id = data["camera_id"]
    fullname = data["fullname"]
    department_id = data["department_id"]
    username = data["username"]
    password = data["password"]

    # Kiểm tra camera_id hợp lệ
    if camera_id not in [1, 2]:
        return jsonify({"error": "Invalid camera_id, must be 1 or 2"}), 400

    # Xác định tên camera và địa chỉ dựa trên camera_id
    camera_name = f"rtsp_camera_{camera_id}"
    camera_address = f"rtsp://192.168.1.142:8554/stream{camera_id}"

    # Tạo ID tự động tăng dần cho camera manager
    last_manager = managers_collection.find_one(sort=[("_id", -1)])
    manager_id = last_manager["_id"] + 1 if last_manager else 1

    # Chuẩn bị dữ liệu để thêm vào MongoDB
    camera_manager = {
        "_id": manager_id,
        "camera_id": camera_id,
        "fullname": fullname,
        "department_id": department_id,
        "username": username,
        "password": password,  # Lưu mật khẩu trực tiếp
        "camera_name": camera_name,
        "camera_address": camera_address,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # Thêm camera manager vào collection
    managers_collection.insert_one(camera_manager)
    return jsonify({
        "message": "Camera manager added successfully",
        "id": manager_id,
        "fullname": fullname,
        "department_id": department_id,
        "username": username,
        "camera_name": camera_name,
        "camera_address": camera_address
    })
# ----------------------------------------------------------------
@app.route('/delete_camera_manager', methods=['DELETE'])
def delete_camera_manager():
    data = request.json

    # Kiểm tra dữ liệu đầu vào
    required_fields = ["username", "password"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    username = data["username"]
    password = data["password"]

    # Kiểm tra camera manager có tồn tại và mật khẩu đúng không
    manager = managers_collection.find_one({"username": username, "password": password})
    if not manager:
        return jsonify({"error": "Invalid username or password"}), 401

    # Lấy _id của camera manager để xử lý xóa
    manager_id = manager["_id"]

    # Xóa camera manager khỏi MongoDB
    result = managers_collection.delete_one({"_id": manager_id})

    if result.deleted_count > 0:
        return jsonify({"message": "Camera manager deleted successfully"}), 200
    else:
        return jsonify({"error": "Failed to delete camera manager"}), 500

# ----------------------------------------------------------------
@app.route('/add_camera', methods=['POST'])
def add_camera():
    data = request.json

    # Kiểm tra dữ liệu đầu vào
    required_fields = ["id_camera", "camera_name", "camera_address", "camera_location"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    id_camera = data["id_camera"]
    camera_name = data["camera_name"]
    camera_address = data["camera_address"]
    camera_location = data["camera_location"]

    # Kiểm tra id_camera có bị trùng không
    existing_camera = camera_collection.find_one({"id_camera": id_camera})
    if existing_camera:
        return jsonify({"error": "Camera ID already exists"}), 400

    # Tạo ID tự động tăng dần cho camera
    last_camera = camera_collection.find_one(sort=[("_id", -1)])
    camera_id = last_camera["_id"] + 1 if last_camera else 1

    # Chuẩn bị dữ liệu để thêm vào MongoDB
    camera_info = {
        "_id": camera_id,
        "id_camera": id_camera,
        "camera_name": camera_name,
        "camera_address": camera_address,
        "camera_location": camera_location,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # Thêm camera vào collection
    camera_collection.insert_one(camera_info)
    return jsonify({
        "message": "Camera added successfully",
        "id": camera_id,
        "id_camera": id_camera,
        "camera_name": camera_name,
        "camera_address": camera_address,
        "camera_location": camera_location
    }), 201


# ----------------------------------------------------------------
@app.route('/emotion_summary', methods=['POST'])
def emotion_summary():
    data = request.json

    # Kiểm tra đầu vào
    required_fields = ["timestamp_start", "timestamp_end", "id", "camera_name"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        timestamp_start = datetime.strptime(data["timestamp_start"], "%Y-%m-%d %H:%M:%S")
        timestamp_end = datetime.strptime(data["timestamp_end"], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return jsonify({"error": "Invalid timestamp format, use 'YYYY-MM-DD HH:MM:SS'"}), 400

    user_id = data["id"]
    camera_name = data["camera_name"]

    # Lọc dữ liệu theo id, camera_name, và khoảng thời gian
    tracking_data = list(data_collection.find({
        "id": user_id,
        "camera_name": camera_name,
        "timestamp": {"$gte": timestamp_start.strftime("%Y-%m-%d %H:%M:%S"),
                      "$lte": timestamp_end.strftime("%Y-%m-%d %H:%M:%S")}
    }))

    if not tracking_data:
        return jsonify({"error": "No tracking data found for the given criteria"}), 404

    # Tìm thông tin user
    user_info = users_collection.find_one({"_id": user_id})
    if not user_info:
        return jsonify({"error": f"User with ID {user_id} not found"}), 404

    # Tính tổng cảm xúc
    emotion_count = {}
    total_emotions = 0
    for record in tracking_data:
        emotion = record["emotion"]
        emotion_prob = record["emotion_prob"]

        if emotion in emotion_count:
            emotion_count[emotion] += emotion_prob
        else:
            emotion_count[emotion] = emotion_prob

        total_emotions += emotion_prob

    if total_emotions == 0:
        return jsonify({"error": "No emotions recorded in the tracking data"}), 404

    # Tính phần trăm từng cảm xúc
    emotion_percentages = {
        emotion: round((prob / total_emotions) * 100, 2)
        for emotion, prob in emotion_count.items()
    }

    # Chuẩn bị dữ liệu trả về
    result = {
        "timestamp_start": timestamp_start.strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp_end": timestamp_end.strftime("%Y-%m-%d %H:%M:%S"),
        "id": user_id,
        "full_name": user_info["full_name"],
        "department_id": user_info["department_id"],
        "emotion_percentages": emotion_percentages
    }

    return jsonify(result), 200
# ----------------------------------------------------------------
@app.route('/get_tracking_data', methods=['POST'])
def get_tracking_data():
    data = request.json

    # Kiểm tra đầu vào
    required_fields = ["timestamp_start", "timestamp_end", "id", "camera_name"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        timestamp_start = datetime.strptime(data["timestamp_start"], "%Y-%m-%d %H:%M:%S")
        timestamp_end = datetime.strptime(data["timestamp_end"], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return jsonify({"error": "Invalid timestamp format, use 'YYYY-MM-DD HH:MM:SS'"}), 400

    user_id = data["id"]
    camera_name = data["camera_name"]

    # Lọc dữ liệu trong khoảng thời gian và camera_name
    tracking_data = list(data_collection.find({
        "id": user_id,
        "camera_name": camera_name,
        "timestamp": {"$gte": timestamp_start.strftime("%Y-%m-%d %H:%M:%S"),
                      "$lte": timestamp_end.strftime("%Y-%m-%d %H:%M:%S")}
    }))

    if not tracking_data:
        return jsonify({"error": "No tracking data found for the given criteria"}), 404

    # Tìm thông tin user
    user_info = users_collection.find_one({"_id": user_id})
    if not user_info:
        return jsonify({"error": f"User with ID {user_id} not found"}), 404

    # Chuyển đổi ObjectId thành chuỗi
    for record in tracking_data:
        record["_id"] = str(record["_id"])  # Chuyển ObjectId thành chuỗi

    # Chuẩn bị kết quả trả về
    result = {
        "timestamp_start": timestamp_start.strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp_end": timestamp_end.strftime("%Y-%m-%d %H:%M:%S"),
        "id": user_id,
        "full_name": user_info["full_name"],
        "department_id": user_info["department_id"],
        "tracking_data": tracking_data
    }
    return jsonify(result), 200
# ----------------------------------------------------------------

@app.route('/get_tracking_data_csv', methods=['POST'])
def get_tracking_data_csv():
    data = request.json

    # Kiểm tra đầu vào
    required_fields = ["timestamp_start", "timestamp_end", "id", "camera_name"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        timestamp_start = datetime.strptime(data["timestamp_start"], "%Y-%m-%d %H:%M:%S")
        timestamp_end = datetime.strptime(data["timestamp_end"], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return jsonify({"error": "Invalid timestamp format, use 'YYYY-MM-DD HH:MM:SS'"}), 400

    user_id = data["id"]
    camera_name = data["camera_name"]

    # Lọc dữ liệu trong khoảng thời gian và camera_name
    tracking_data = list(data_collection.find({
        "id": user_id,
        "camera_name": camera_name,
        "timestamp": {"$gte": timestamp_start.strftime("%Y-%m-%d %H:%M:%S"),
                      "$lte": timestamp_end.strftime("%Y-%m-%d %H:%M:%S")}
    }))

    if not tracking_data:
        return jsonify({"error": "No tracking data found for the given criteria"}), 404

    # Chuyển đổi ObjectId thành chuỗi
    for record in tracking_data:
        record["_id"] = str(record["_id"])

    # Tạo CSV trong bộ nhớ
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=tracking_data[0].keys())
    writer.writeheader()
    writer.writerows(tracking_data)

    # Trả về CSV dưới dạng response
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=tracking_data.csv"}
    )

# Chạy ứng dụng Flask
if __name__ == "__main__":
    app.run(debug=True, port=6123)