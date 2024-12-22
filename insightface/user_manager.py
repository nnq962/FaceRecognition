from flask import Flask, jsonify, request
import json
import os

app = Flask(__name__)

# Đường dẫn tới tệp JSON
JSON_FILE = "users.json"

# Hàm để tải dữ liệu từ tệp JSON
def load_data():
    """Tải dữ liệu từ tệp JSON hoặc khởi tạo nếu không tồn tại."""
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r") as file:
            return json.load(file)
    return {"users": {}, "user_id_counter": 1}

# Hàm để lưu dữ liệu vào tệp JSON
def save_data(data):
    """Lưu dữ liệu vào tệp JSON."""
    with open(JSON_FILE, "w") as file:
        json.dump(data, file, indent=4)

# Dữ liệu được tải khi ứng dụng bắt đầu
data = load_data()

@app.route("/users", methods=["POST"])
def add_user():
    """Thêm người dùng mới."""
    user_info = request.get_json()
    username = user_info.get("username")
    password = user_info.get("password")
    departmentid = user_info.get("departmentid")

    if not username or not password or departmentid is None:
        return jsonify({"error": "Missing username, password, or departmentid"}), 400

    if username in data["users"]:
        return jsonify({"error": "Username already exists"}), 409

    # Tạo người dùng mới
    userid = data["user_id_counter"]
    data["users"][username] = {"userid": userid, "password": password, "departmentid": departmentid}
    data["user_id_counter"] += 1
    save_data(data)

    return jsonify({"message": "User added successfully", "user": data["users"][username]}), 201

@app.route("/users", methods=["GET"])
def view_users():
    """Xem danh sách người dùng."""
    return jsonify(data["users"])

@app.route("/users/<username>", methods=["PUT"])
def update_user(username):
    """Cập nhật thông tin người dùng."""
    if username not in data["users"]:
        return jsonify({"error": "User not found"}), 404

    user_info = request.get_json()
    password = user_info.get("password")
    departmentid = user_info.get("departmentid")

    if password:
        data["users"][username]["password"] = password
    if departmentid is not None:
        data["users"][username]["departmentid"] = departmentid

    save_data(data)
    return jsonify({"message": "User updated successfully", "user": data["users"][username]}), 200

@app.route("/users/<username>", methods=["DELETE"])
def delete_user(username):
    """Xóa người dùng."""
    if username not in data["users"]:
        return jsonify({"error": "User not found"}), 404

    del data["users"][username]
    save_data(data)
    return jsonify({"message": f"User '{username}' deleted successfully"}), 200

@app.route("/users/<username>/faces", methods=["POST"])
def add_face_image(username):
    """Thêm ảnh khuôn mặt cho người dùng."""
    if username not in data["users"]:
        return jsonify({"error": "User not found"}), 404

    # Lấy thông tin ảnh từ request
    face_image = request.files.get("face_image")
    if not face_image:
        return jsonify({"error": "No face image provided"}), 400

    # Lưu ảnh theo user_id
    user_id = data["users"][username]["userid"]
    save_dir = os.path.join("faces", str(user_id))
    os.makedirs(save_dir, exist_ok=True)
    face_path = os.path.join(save_dir, face_image.filename)
    face_image.save(face_path)

    # Thêm thông tin ảnh vào dữ liệu người dùng
    data["users"][username].setdefault("faces", []).append(face_path)
    save_data(data)

    return jsonify({
        "message": "Face image added successfully",
        "faces": data["users"][username]["faces"]
    }), 200

if __name__ == "__main__":
    app.run(debug=True)